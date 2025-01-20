import logging
import os
from logging.handlers import RotatingFileHandler
from colorlog import ColoredFormatter


class Logger:
    @staticmethod
    def get_logger(
            name: str,
            log_file: str = "application.log",
            max_bytes: int = 5 * 1024 * 1024,
            backup_count: int = 3,
    ):
        """
        Создает настроенный логгер с цветным и табличным форматированием.

        :param name: Имя логгера
        :param log_file: Файл, в который будут записываться логи
        :param max_bytes: Максимальный размер файла лога (по умолчанию: 5MB)
        :param backup_count: Количество резервных файлов лога
        :return: Настроенный логгер
        """
        logger = logging.getLogger(name)
        if logger.hasHandlers():
            return logger  # Если логгер уже настроен, не настраиваем его повторно

        logger.setLevel(logging.INFO)

        # Формат сообщений с цветами для консоли
        color_formatter = ColoredFormatter(
            "%(log_color)s%(asctime)-20s | %(name)-25s | %(levelname)-7s | %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )

        # Консольный хендлер с цветным выводом
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(color_formatter)
        logger.addHandler(console_handler)

        # Хендлер для записи в файл
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        logger.addHandler(file_handler)

        return logger