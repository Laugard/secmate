from __future__ import annotations

import discord


def split_message(text: str, limit: int = 1900) -> list[str]:
    if not text:
        return ["(tomt svar)"]
    parts: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            parts.append(remaining)
            break
        cut = max(remaining.rfind("\n", 0, limit), remaining.rfind(" ", 0, limit))
        if cut <= 0:
            cut = limit
        parts.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return parts


NO_MENTIONS = discord.AllowedMentions.none()
