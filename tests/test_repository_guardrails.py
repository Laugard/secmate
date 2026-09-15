from pathlib import Path


def test_runtime_files_are_ignored() -> None:
    text = Path(".gitignore").read_text(encoding="utf-8")
    for expected in (
        ".env",
        "data/*.db",
        "data/documents/*",
        "data/backups/*",
        "logs/*",
        "*.sqlite",
    ):
        assert expected in text


def test_no_privileged_intents() -> None:
    text = Path("src/secmate/app.py").read_text(encoding="utf-8")
    assert "discord.Intents.none()" in text
    assert "message_content" not in text
