import logging
from logging.handlers import RotatingFileHandler


def configure_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s - %(message)s"
    )

    # Console
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Rotating file (avoid filling SD card)
    fh = RotatingFileHandler(
        "spirulina.log", maxBytes=2_000_000, backupCount=5
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Silence noisy httpx request logging
    logging.getLogger("httpx").setLevel(logging.WARNING)
