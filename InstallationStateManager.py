import os
import json

from logger_config import Logger
logger = Logger.get_logger(__name__)


class InstallationStateManager:
    def __init__(self, state_file_path):
        self.state_file_path = state_file_path
        self.state = self.load_state()


    def clear_state_file(self, use_logger: bool = True):
        """
        Полностью очищает файл состояния, удаляя все данные.
        """
        if os.path.exists(self.state_file_path):
            if use_logger:
                logger.info(f"Очищаю файл состояния: {self.state_file_path}")
            with open(self.state_file_path, "w") as file:
                file.write("{}")  # Записываем пустой JSON объект
            self.state = {}  # Очищаем текущее состояние в памяти
        else:
            logger.warning(f"Файл состояния {self.state_file_path} не существует. Очищать нечего.")


    def load_state(self):
        """
        Загружает состояние из файла, если он существует.
        """
        if os.path.exists(self.state_file_path):
            with open(self.state_file_path, "r") as file:
                try:
                    return json.load(file)
                except json.JSONDecodeError:
                    logger.error("Ошибка при чтении файла состояния. Использую пустое состояние.")
                    return {}
        return {}


    def save_state(self):
        """
        Сохраняет текущее состояние в файл.
        """
        with open(self.state_file_path, "w") as file:
            json.dump(self.state, file, indent=4)
        logger.info("Состояние сохранено.")


    def add_installed_component(self, installed_component_name, path):
        """
        Добавляет компонент в состояние.
        """
        if installed_component_name in self.state:
            logger.warning(f"Компонент '{installed_component_name}' уже существует в конфиге. Перезаписываю путь.")
        self.state[installed_component_name] = path
        logger.info(f"Добавлен компонент '{installed_component_name}' с путём '{path}'.")
        self.save_state()


    def get_installed_component_path(self, installed_component_name):
        """
        Возвращает путь к указанному компоненту по ключу.
        """
        if installed_component_name in self.state:
            return self.state[installed_component_name]
        logger.warning(f"Компонент '{installed_component_name}' не найден в конфиге.")
        return None


    def remove_installed_component(self, installed_component_name):
        """
        Удаляет компонент из состояния установки.
        """
        if installed_component_name in self.state:
            del self.state[installed_component_name]
            logger.info(f"Компонент '{installed_component_name}' удалён из конфига.")
            self.save_state()
        else:
            logger.warning(f"Компонент '{installed_component_name}' не найден в конфиге. Удалять нечего.")
