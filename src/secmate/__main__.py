from secmate.app import SecMateClient
from secmate.config import Settings
from secmate.logging_config import configure_logging


def main() -> None:
    settings = Settings.from_env()
    settings.ensure_directories()
    configure_logging(settings.log_path, settings.log_level)
    SecMateClient(settings).run(settings.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
