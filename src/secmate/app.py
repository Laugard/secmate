"""Discord client, slash commands, and idempotent scheduled work."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import tasks

from secmate.config import Settings
from secmate.errors import SecMateError, ValidationError
from secmate.repositories.database import (
    Database,
    DeadlineRepository,
    DocumentRepository,
    JobRepository,
    MemoryRepository,
    NewsRepository,
    backup_database,
    cleanup,
)
from secmate.services.agent_service import AgentService
from secmate.services.digest_service import DigestService
from secmate.services.ingestion_service import IngestionService
from secmate.services.news_service import FeedClient, NewsService
from secmate.services.ollama_service import OllamaService
from secmate.services.rag_service import RagService
from secmate.utils.discord_text import NO_MENTIONS, split_message
from secmate.utils.time import local_deadline_to_utc, parse_utc
from secmate.utils.validation import bounded_text, reject_likely_secret

LOGGER = logging.getLogger(__name__)


def minimal_intents() -> discord.Intents:
    intents = discord.Intents.none()
    intents.guilds = True
    return intents


def is_admin(interaction: discord.Interaction[Any], admin_role_id: int | None) -> bool:
    permissions = getattr(interaction.user, "guild_permissions", None)
    if permissions and permissions.manage_guild:
        return True
    roles = getattr(interaction.user, "roles", ())
    return bool(admin_role_id and any(getattr(role, "id", None) == admin_role_id for role in roles))


async def require_admin(interaction: discord.Interaction[Any], role_id: int | None) -> bool:
    if is_admin(interaction, role_id):
        return True
    await interaction.response.send_message(
        "Du skal have Manage Server eller SecMate-adminrollen.",
        ephemeral=True,
        allowed_mentions=NO_MENTIONS,
    )
    return False


async def followup_parts(interaction: discord.Interaction[Any], text: str) -> None:
    for part in split_message(text):
        await interaction.followup.send(part, allowed_mentions=NO_MENTIONS)


class SecMateClient(discord.Client):
    def __init__(self, settings: Settings) -> None:
        super().__init__(intents=minimal_intents(), allowed_mentions=NO_MENTIONS)
        self.settings = settings
        self.tree = app_commands.CommandTree(self)
        self.database = Database(settings.database_path)
        self.memories = MemoryRepository(self.database)
        self.deadlines = DeadlineRepository(self.database)
        self.documents = DocumentRepository(self.database)
        self.news_repository = NewsRepository(self.database)
        self.jobs = JobRepository(self.database)
        self.ollama = OllamaService(
            settings.ollama_host,
            settings.ollama_chat_model,
            settings.ollama_embed_model,
            settings.ollama_timeout,
        )
        self.rag = RagService(
            self.documents, self.ollama, settings.rag_top_k, settings.rag_min_similarity
        )
        self.ingestion = IngestionService(
            self.documents,
            self.ollama,
            settings.documents_path,
            max_bytes=settings.max_document_bytes,
            max_pages=settings.max_document_pages,
            chunk_chars=settings.rag_chunk_chars,
            overlap_chars=settings.rag_chunk_overlap_chars,
        )
        self.news = NewsService(
            self.news_repository,
            self.ollama,
            FeedClient(
                settings.news_feed_urls,
                settings.news_http_timeout,
                settings.news_max_response_bytes,
            ),
            settings.news_retention_days,
        )
        self.digest = DigestService(self.deadlines, self.documents, self.ollama)
        self._register_commands()

    async def setup_hook(self) -> None:
        await self.database.migrate()
        guild = discord.Object(id=self.settings.discord_test_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        if not self.scheduler.is_running():
            self.scheduler.start()

    async def close(self) -> None:
        if self.scheduler.is_running():
            self.scheduler.cancel()
        await super().close()

    async def post_news_items(self, items: list[dict[str, Any]]) -> int:
        posted = 0
        for item in items:
            channel_id = self.settings.news_channel_ids.get(str(item["category"]))
            channel = self.get_channel(channel_id) if channel_id else None
            if not isinstance(channel, discord.abc.Messageable):
                LOGGER.warning(
                    "news_post_skipped reason=missing_channel category=%s", item["category"]
                )
                continue
            text = (
                f"**{item['title']}** [{item['category']}]\n"
                f"AI-resumé: {item['summary_da']}\n"
                f"Studierelevans: {item['study_relevance_da']}\n<{item['url']}>"
            )
            await channel.send(text[:1900], allowed_mentions=NO_MENTIONS)
            await self.news_repository.mark_posted(str(item["id"]))
            posted += 1
        return posted

    def _register_commands(self) -> None:
        @self.tree.command(name="health", description="Vis SecMate-systemets status")
        async def health(interaction: discord.Interaction[Any]) -> None:
            await interaction.response.defer(thinking=True)
            db_ok = await self.database.integrity_check()
            documents, chunks = await self.documents.counts()
            try:
                ai = await self.ollama.health()
            except Exception:
                ai = {"api": False, "chat_model": False, "embed_model": False}

            def icon(value: bool) -> str:
                return "🟢" if value else "🔴"

            text = (
                f"{icon(db_ok)} Database\n{icon(ai['api'])} Ollama API\n"
                f"{icon(ai['chat_model'])} Chatmodel `{self.settings.ollama_chat_model}`\n"
                f"{icon(ai['embed_model'])} Embeddingmodel `{self.settings.ollama_embed_model}`\n"
                f"{'🟢' if chunks else '🟡'} Dokumentindeks: {documents} dokumenter / {chunks} chunks\n"
                f"{'🟢' if self.settings.digest_channel_id else '🟡'} Digest-kanal"
            )
            await followup_parts(interaction, text)

        @self.tree.command(name="ask", description="Spørg de lokale studiedokumenter")
        async def ask(interaction: discord.Interaction[Any], question: str) -> None:
            await interaction.response.defer(thinking=True)
            question = bounded_text(question, self.settings.max_prompt_chars, "Spørgsmålet")
            await followup_parts(interaction, await self.rag.answer(question))

        @self.tree.command(name="remember", description="Gem en ufølsom fælles note")
        async def remember(interaction: discord.Interaction[Any], text: str) -> None:
            text = bounded_text(text, self.settings.max_memory_chars, "Noten")
            reject_likely_secret(text)
            item = await self.memories.add(
                str(interaction.guild_id), text, self.settings.memory_retention_days
            )
            await interaction.response.send_message(
                f"Gemt som `{item.id}`. Gem ikke persondata, adgangskoder eller private oplysninger.",
                ephemeral=True,
                allowed_mentions=NO_MENTIONS,
            )

        @self.tree.command(name="memories", description="Vis aktive fælles noter")
        async def memories(interaction: discord.Interaction[Any]) -> None:
            items = await self.memories.list_active(str(interaction.guild_id))
            text = (
                "\n".join(f"`{item.id}` — {item.content}" for item in items)
                or "Ingen aktive noter."
            )
            await interaction.response.send_message(text[:1900], allowed_mentions=NO_MENTIONS)

        @self.tree.command(name="forget", description="Slet en fælles note (admin)")
        async def forget(interaction: discord.Interaction[Any], memory_id: str) -> None:
            if not await require_admin(interaction, self.settings.admin_role_id):
                return
            deleted = await self.memories.delete(str(interaction.guild_id), memory_id)
            await interaction.response.send_message(
                "Noten er slettet." if deleted else "Noten blev ikke fundet.",
                ephemeral=True,
                allowed_mentions=NO_MENTIONS,
            )

        deadline_group = app_commands.Group(name="deadlines", description="Administrér deadlines")

        @deadline_group.command(name="add", description="Tilføj deadline (admin)")
        async def deadline_add(
            interaction: discord.Interaction[Any],
            title: str,
            due_date: str,
            due_time: str | None = None,
        ) -> None:
            if not await require_admin(interaction, self.settings.admin_role_id):
                return
            title = bounded_text(title, 120, "Titlen")
            item = await self.deadlines.add(
                str(interaction.guild_id),
                title,
                local_deadline_to_utc(due_date, due_time, self.settings.timezone),
            )
            await interaction.response.send_message(
                f"Deadline `{item.id}` er gemt.", allowed_mentions=NO_MENTIONS
            )

        @deadline_group.command(name="list", description="Vis kommende deadlines")
        async def deadline_list(interaction: discord.Interaction[Any]) -> None:
            items = await self.deadlines.list_pending(str(interaction.guild_id))
            now = datetime.now(UTC)
            lines = []
            for item in items:
                due = parse_utc(item.due_at_utc)
                local = due.astimezone(self.settings.timezone)
                remaining = due - now
                lines.append(
                    f"`{item.id}` — {item.title}: {local:%Y-%m-%d %H:%M} ({max(0, int(remaining.total_seconds() // 3600))} timer)"
                )
            await interaction.response.send_message(
                "\n".join(lines)[:1900] or "Ingen kommende deadlines.", allowed_mentions=NO_MENTIONS
            )

        @deadline_group.command(name="complete", description="Markér deadline færdig (admin)")
        async def deadline_complete(
            interaction: discord.Interaction[Any], deadline_id: str
        ) -> None:
            if not await require_admin(interaction, self.settings.admin_role_id):
                return
            ok = await self.deadlines.complete(str(interaction.guild_id), deadline_id)
            await interaction.response.send_message(
                "Deadline markeret færdig." if ok else "Deadline blev ikke fundet.",
                allowed_mentions=NO_MENTIONS,
            )

        @deadline_group.command(name="delete", description="Slet deadline (admin)")
        async def deadline_delete(interaction: discord.Interaction[Any], deadline_id: str) -> None:
            if not await require_admin(interaction, self.settings.admin_role_id):
                return
            ok = await self.deadlines.delete(str(interaction.guild_id), deadline_id)
            await interaction.response.send_message(
                "Deadline slettet." if ok else "Deadline blev ikke fundet.",
                allowed_mentions=NO_MENTIONS,
            )

        self.tree.add_command(deadline_group)

        @self.tree.command(name="today", description="Vis ugens deadlines og dagens fokus")
        async def today(interaction: discord.Interaction[Any]) -> None:
            await interaction.response.defer(thinking=True)
            await followup_parts(
                interaction, await self.digest.build(str(interaction.guild_id), datetime.now(UTC))
            )

        @self.tree.command(name="reindex", description="Genindeksér lokale dokumenter (admin)")
        async def reindex(interaction: discord.Interaction[Any]) -> None:
            if not await require_admin(interaction, self.settings.admin_role_id):
                return
            await interaction.response.defer(thinking=True)
            report = await self.ingestion.ingest_all()
            await followup_parts(
                interaction,
                f"Indekseret: {report.indexed}; uændret: {report.unchanged}; chunks: {report.chunks}; fejl: {len(report.errors)}",
            )

        news_group = app_commands.Group(name="news", description="Sikkerhedsnyheder")

        @news_group.command(name="latest", description="Vis seneste gemte nyheder")
        async def news_latest(
            interaction: discord.Interaction[Any], category: str = "alle"
        ) -> None:
            if category not in {*self.settings.news_channel_ids, "alle"}:
                raise ValidationError("Ukendt kategori")
            items = await self.news_repository.latest(category)
            text = (
                "\n\n".join(
                    f"**{item['title']}** [{item['category']}]\nAI-resumé: {item['summary_da']}\n<{item['url']}>"
                    for item in items
                )
                or "Ingen gemte nyheder."
            )
            await interaction.response.send_message(text[:1900], allowed_mentions=NO_MENTIONS)

        @news_group.command(name="refresh", description="Hent feeds nu (admin)")
        async def news_refresh(interaction: discord.Interaction[Any]) -> None:
            if not await require_admin(interaction, self.settings.admin_role_id):
                return
            await interaction.response.defer(thinking=True)
            items, errors = await self.news.refresh(self.settings.news_max_items_per_run)
            posted = await self.post_news_items(items)
            await followup_parts(
                interaction,
                f"Nye nyheder: {len(items)}; postet: {posted}; feedfejl: {len(errors)}",
            )

        self.tree.add_command(news_group)

        async def search_tool(args: dict[str, Any]) -> str:
            query = bounded_text(
                str(args.get("query", "")), self.settings.max_prompt_chars, "query"
            )
            return (
                "\n".join(f"{m.citation}: {m.chunk.content}" for m in await self.rag.search(query))
                or "Ingen belæg."
            )

        async def deadlines_tool(args: dict[str, Any]) -> str:
            days = min(max(int(args.get("days_ahead", 7)), 1), 90)
            items = await self.deadlines.list_pending(
                str(self.settings.discord_test_guild_id),
                until=datetime.now(UTC) + timedelta(days=days),
            )
            return "\n".join(f"{i.title}: {i.due_at_utc}" for i in items) or "Ingen deadlines."

        async def memories_tool(args: dict[str, Any]) -> str:
            items = await self.memories.list_active(str(self.settings.discord_test_guild_id), 5)
            return "\n".join(i.content for i in items) or "Ingen noter."

        async def latest_news_tool(args: dict[str, Any]) -> str:
            category = str(args.get("category", "alle"))
            limit = min(max(int(args.get("limit", 5)), 1), 5)
            items = await self.news_repository.latest(category, limit)
            return "\n".join(f"{i['title']} <{i['url']}>" for i in items) or "Ingen nyheder."

        agent = AgentService(
            self.ollama,
            {
                "search_documents": search_tool,
                "list_deadlines": deadlines_tool,
                "list_memories": memories_tool,
                "latest_news": latest_news_tool,
            },
        )

        @self.tree.command(name="assistant", description="Kombinér read-only SecMate-kilder")
        async def assistant(interaction: discord.Interaction[Any], request: str) -> None:
            await interaction.response.defer(thinking=True)
            request = bounded_text(request, self.settings.max_prompt_chars, "Forespørgslen")
            answer, activity = await agent.run(request)
            suffix = "\n\nVærktøjer: " + ", ".join(activity) if activity else ""
            await followup_parts(interaction, answer + suffix)

        @self.tree.error
        async def on_error(
            interaction: discord.Interaction[Any], error: app_commands.AppCommandError
        ) -> None:
            original = getattr(error, "original", error)
            message = (
                str(original)
                if isinstance(original, SecMateError)
                else "Der opstod en sikker intern fejl. Prøv igen."
            )
            LOGGER.warning("command_failed type=%s", type(original).__name__)
            if interaction.response.is_done():
                await interaction.followup.send(
                    message, ephemeral=True, allowed_mentions=NO_MENTIONS
                )
            else:
                await interaction.response.send_message(
                    message, ephemeral=True, allowed_mentions=NO_MENTIONS
                )

    @tasks.loop(minutes=1)
    async def scheduler(self) -> None:
        now = datetime.now(UTC)
        local = now.astimezone(self.settings.timezone)
        guild_id = str(self.settings.discord_test_guild_id)
        if (
            local.strftime("%H:%M") >= self.settings.digest_time_local
            and self.settings.digest_channel_id
        ):
            job_id = await self.jobs.claim("daily_digest", guild_id, local.date().isoformat())
            if job_id:
                try:
                    channel = self.get_channel(self.settings.digest_channel_id)
                    if isinstance(channel, discord.abc.Messageable):
                        await channel.send(
                            await self.digest.build(guild_id, now), allowed_mentions=NO_MENTIONS
                        )
                        await self.jobs.finish(job_id, True)
                    else:
                        await self.jobs.finish(job_id, False, "missing_channel")
                except Exception:
                    await self.jobs.finish(job_id, False, "send_failed")
        if (
            local.strftime("%H:%M") >= self.settings.news_time_local
            and self.settings.news_feed_urls
        ):
            news_job = await self.jobs.claim("daily_news", guild_id, local.date().isoformat())
            if news_job:
                try:
                    items, _errors = await self.news.refresh(self.settings.news_max_items_per_run)
                    await self.post_news_items(items)
                    await self.jobs.finish(news_job, True)
                except Exception:
                    await self.jobs.finish(news_job, False, "news_failed")
        if local.hour == 2 and local.minute == 0:
            cleanup_job = await self.jobs.claim("daily_cleanup", guild_id, local.date().isoformat())
            if cleanup_job:
                try:
                    await cleanup(
                        self.database, now, self.settings.completed_deadline_retention_days
                    )
                    await backup_database(self.database, self.settings.backup_path)
                    await self.jobs.finish(cleanup_job, True)
                except Exception:
                    await self.jobs.finish(cleanup_job, False, "maintenance_failed")

    @scheduler.before_loop
    async def before_scheduler(self) -> None:
        await self.wait_until_ready()
