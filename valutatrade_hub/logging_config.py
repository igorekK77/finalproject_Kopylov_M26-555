import logging
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging() -> logging.Logger:
    """Настраивает логирование с ротацией файлов по размеру."""
    settings = SettingsLoader()

    log_path = settings.get("log_file", "logs/actions.log")

    logger = logging.getLogger("valutatrade_hub")
    logger.setLevel(settings.get("log_level", "INFO").upper())

    if logger.handlers:
        return logger

    handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        fmt=settings.get(
            "log_format",
            "%(levelname)s %(asctime)s %(message)s"
        ),
        datefmt=settings.get(
            "log_date_format",
            "%Y-%m-%dT%H:%M:%S"
        )
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger