import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


class DotTimeFormatter(logging.Formatter):
    """
    Formato de tiempo personalizado:
    YYYY.MM.DD HH:MM:SS
    """

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%Y.%m.%d %H:%M:%S")


def setup_logging(
    log_dir: str = "logs",
    log_file: str = "bot.log",
    level: int = logging.INFO,
) -> None:
    """
    Configura el sistema de logging:
    - salida a archivo con rotación
    - salida a consola
    - formato consistente
    """

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    formatter = DotTimeFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )


    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)


    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if not root_logger.handlers:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
