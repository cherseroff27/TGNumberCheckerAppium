import logging
import os
from logging.handlers import RotatingFileHandler
from colorlog import ColoredFormatter
import re


class ThreadMessageFilter(logging.Filter):
    """
    Фильтр для замены текста ThreadPoolExecutor-0_<номер> на "Поток Номер <номер + 1>" в сообщениях.
    """
    thread_message_pattern = re.compile(r"ThreadPoolExecutor-\d+_(\d+)")

    def filter(self, record):
        # Заменяем все вхождения в тексте сообщения
        if hasattr(record, "message"):
            record.message = self.thread_message_pattern.sub(
                lambda m: f"Поток Номер {int(m.group(1)) + 1}",
                record.getMessage()
            )
        # Также заменяем текст в аргументах, если они есть
        if record.args:
            record.args = tuple(
                self.thread_message_pattern.sub(
                    lambda m: f"Поток Номер {int(m.group(1)) + 1}", str(arg)
                ) for arg in record.args
            )
        return True


class Logger:
    @staticmethod
    def get_logger(name: str, log_file: str = "application.log", max_bytes: int = 5 * 1024 * 1024, backup_count: int = 3):
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

        # Формат для файлового лога (без цветов)
        file_formatter = logging.Formatter(
            "%(asctime)-20s | %(name)-20s | %(levelname)-7s | %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S',
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
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Добавляем фильтр для преобразования сообщений
        logger.addFilter(ThreadMessageFilter())

        return logger