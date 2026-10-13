import logging
import sys


def configure_logging(env: str = "development") -> None:
    logging.basicConfig(
        level=logging.INFO if env == "production" else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
