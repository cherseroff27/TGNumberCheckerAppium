import json
import os

from logger_config import Logger
logger = Logger.get_logger(__name__)


class LocalVariablesManager:
    def __init__(self):
        pass

    @staticmethod
    def get_all_local_env_vars():
        """Получает список локальных переменных окружения процесса"""
        # Преобразовать в JSON
        env_vars = dict(os.environ)  # Получаем переменные окружения
        env_vars_json = json.dumps(env_vars, indent=4)  # Форматируем в JSON
        logger.info("Текущие переменные окружения:\n" + env_vars_json)
        return env_vars  # Возвращаем словарь переменных окружения

    @staticmethod
    def add_to_local_env_path_var(new_path):
        """Добавляет путь в переменную PATH локального окружения."""
        os.environ["PATH"] = os.pathsep.join([new_path, os.environ.get("PATH", "")])
        logger.info(f"Добавлен путь в PATH: {new_path}")

    @staticmethod
    def add_to_local_env_var(variable_name, value):
        """Устанавливает локальную переменную окружения."""
        os.environ[variable_name] = value
        logger.info(f"Установлена переменная среды: {variable_name} = {value}")