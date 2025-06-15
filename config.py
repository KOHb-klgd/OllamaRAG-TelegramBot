import os
import logging
from logging.handlers import RotatingFileHandler
import colorlog
from dataclasses import dataclass
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()


@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    PROXY_URL: str = os.getenv("PROXY_URL", None)  # Поддержка прокси через переменную окружения
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "bambucha/saiga-llama3")


def setup_logger():
    """Настраивает цветное логирование."""
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Логирование в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Логирование в файл
    file_handler = RotatingFileHandler(
        "bot.log", maxBytes=1000000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(file_handler)

    return logger


# Настройка логгера
logger = setup_logger()
