import secrets


def public_id(prefix: str) -> str:
    """Return a short non-sequential public identifier."""
    return f"{prefix}_{secrets.token_urlsafe(9)}"
