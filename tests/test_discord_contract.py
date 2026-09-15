from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import discord

from secmate.app import is_admin
from secmate.utils.discord_text import NO_MENTIONS


def test_admin_permission_fail_closed() -> None:
    denied = SimpleNamespace(
        user=SimpleNamespace(guild_permissions=SimpleNamespace(manage_guild=False), roles=[])
    )
    allowed = SimpleNamespace(
        user=SimpleNamespace(guild_permissions=SimpleNamespace(manage_guild=True), roles=[])
    )
    assert not is_admin(denied, None)  # type: ignore[arg-type]
    assert is_admin(allowed, None)  # type: ignore[arg-type]


def test_allowed_mentions_are_disabled() -> None:
    assert isinstance(NO_MENTIONS, discord.AllowedMentions)
    assert NO_MENTIONS.everyone is False
    assert NO_MENTIONS.users is False
    assert NO_MENTIONS.roles is False


def test_slow_commands_defer_before_work() -> None:
    source = Path("src/secmate/app.py").read_text(encoding="utf-8")
    for command in ("ask", "reindex", "assistant"):
        marker = f"async def {command}("
        body = source[source.index(marker) :]
        assert body.index("interaction.response.defer") < body.index("await self.")
