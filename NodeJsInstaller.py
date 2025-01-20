import os
import platform
import requests

from InstallationStateManager import InstallationStateManager
from LocalVariablesManager import LocalVariablesManager
from PackageManager import PackageManager

from logger_config import Logger
logger = Logger.get_logger(__name__)


class NodeJsInstaller:
    def __init__(self, temp_files_dir, node_dir, base_project_dir):
        self.temp_files_dir = temp_files_dir
        self.node_dir = node_dir

        self.local_variables_manager = LocalVariablesManager()
        self.package_manager = PackageManager()

        self.state_file_path = os.path.join(base_project_dir, "node_js_installation_state.json")
        self.installation_state_manager = InstallationStateManager(self.state_file_path)

        # Базовый URL для скачивания Node.js
        self.node_base_url = "https://nodejs.org/dist/latest/"


    def setup_all(self):
        """Комплексная установка всех компонентов."""
        self.initial_environment_setup()


    def initial_environment_setup(self):
        """Выполняет настройку локальных переменных среды для всех инструментов."""
        self._ensure_tool(
            setup_function=self.setup_node,
            tool_key="node_js_installed_path_key",
            env_var_name="NODE_HOME",
            additional_paths=[os.path.join(self.node_dir, "node_modules", "npm", "bin")]
        )
        self._ensure_tool(
            setup_function=self.setup_npm,
            tool_key="npm_installed_path_key",
            env_var_name="NPM",
        )


    def _ensure_tool(self, setup_function, tool_key, env_var_name=None, additional_paths=None):
        """Убедиться, что инструмент установлен, и при необходимости выполнить установку."""
        if not self._load_tool(tool_key, env_var_name, additional_paths):
            setup_function()


    def _load_tool(self, tool_key, env_var_name=None, additional_paths=None):
        """Загружает инструмент из состояния или выполняет установку."""
        tool_path = self.installation_state_manager.get_installed_component_path(tool_key)

        if not tool_path or not os.path.exists(tool_path):
            logger.info(f"Инструмент '{tool_key}' не найден, требуется установка. Начинаем установку...")
            self.installation_state_manager.remove_installed_component(tool_key)
            return False

        logger.info(f"Путь к инструменту '{tool_key}' найден: {tool_path}")

        if env_var_name:
            LocalVariablesManager.add_to_local_env_var(env_var_name, tool_path)
        if additional_paths:
            for path in additional_paths:
                LocalVariablesManager.add_to_local_env_path_var(path)
        return True


    @staticmethod
    def is_64bit_system():
        """Проверяет, является ли система 64-битной."""
        return platform.architecture()[0] == "64bit"


    def get_node_download_url(self):
        """Формирует URL для скачивания последней версии Node.js в зависимости от разрядности системы."""
        bitness = "x64" if self.is_64bit_system() else "x86"
        index_url = "https://nodejs.org/dist/index.json"

        try:
            response = requests.get(index_url)
            response.raise_for_status()
            versions = response.json()
            latest_version = versions[0]["version"]  # Берём последнюю версию из списка
            logger.info(f"Определена последняя версия Node.js: {latest_version}")
            return f"https://nodejs.org/dist/{latest_version}/node-{latest_version}-win-{bitness}.zip"
        except Exception as e:
            logger.error(f"Ошибка при определении последней версии Node.js: {e}")
            raise Exception("Не удалось определить последнюю версию Node.js.")


    def fetch_node_version(self):
        """Проверяет версию Node.js, что будет свидетельствовать о его доступности."""
        version = self.package_manager.fetch_package_version("node")
        return version is not False


    def download_node(self):
        """Метод для скачивания Node.js в папку временных файлов."""
        logger.info(f"Начинаем скачивание временных файлов Node.js в папку {self.temp_files_dir}...")

        try:
            node_download_url = self.get_node_download_url()

            # Скачиваем архив с бинарными файлами и библиотеками Node.js
            downloaded_archive_path = self.package_manager.download_tool(
                filename="Node.js",
                url=node_download_url,
                target_dir=self.temp_files_dir,
            )
            return downloaded_archive_path
        except Exception as e:
            logger.error(f"Ошибка при скачивании Node.js: {e}")
            raise Exception("Не удалось скачать Node.js.")


    def unpack_node(self, downloaded_archive_path):
        if downloaded_archive_path is None:
            raise ValueError("Путь к архиву не может быть None. Убедитесь, что скачивание было выполнено.")

        # Распаковываем в директорию "NODE"
        self.package_manager.unpack_tool(archive_path=downloaded_archive_path, target_dir=self.node_dir, extract_top_folder=False)

        # Получаем путь к Node.js
        node_home = self.node_dir
        if not node_home:
            raise Exception("Директория Node.js оказалась пустой после распаковки.")

        return node_home


    def setup_node(self):
        """Последовательно выполняем команды скачивания, распаковки Node.js и добавляем в переменные среды"""
        if self.fetch_node_version():
            logger.info("Node.js уже установлен. Пропускаем установку.")
            return

        downloaded_archive_path = self.download_node()
        if downloaded_archive_path is None:
            logger.error(f"Путь скачанного архива Node.js: {downloaded_archive_path}")
            return

        node_home = self.unpack_node(downloaded_archive_path)

        self.installation_state_manager.add_installed_component("node_js_installed_path_key", node_home)

        LocalVariablesManager.add_to_local_env_path_var(os.path.join(self.node_dir, "node_modules", "npm", "bin"))
        LocalVariablesManager.add_to_local_env_var("NODE_HOME", node_home)

        logger.info("Node.js успешно установлен.")


    def setup_npm(self):
        """Добавляем NPM в локальные переменные окружения"""
        npm_path = os.path.join(self.node_dir, "node_modules", "npm", "bin")
        self.installation_state_manager.add_installed_component("npm_installed_path_key", npm_path)
        LocalVariablesManager.add_to_local_env_var("NPM", npm_path)


    def verify_node_js_environment_setup(self):
        """
        Проверяет корректность установленных переменных среды и содержимого PATH.
        Returns: bool: True, если все переменные и пути корректны, иначе False.
        """
        variables_to_check = {
            "NODE_HOME": self.node_dir,
        }

        paths_to_check = [
            os.path.join(self.node_dir, "node_modules", "npm", "bin"),
        ]

        all_correct = True

        # Проверяем переменные среды
        for var, expected_path in variables_to_check.items():
            actual_path = os.environ.get(var)
            if actual_path != expected_path:
                logger.error(
                    f"Переменная окружения {var} установлена некорректно. Ожидалось: {expected_path}, найдено: {actual_path}")
                all_correct = False
            else:
                logger.info(f"Переменная окружения {var} установлена корректно: {actual_path}")

        # Проверяем пути в PATH
        path_env = os.environ.get("PATH", "")
        for path in paths_to_check:
            if path not in path_env:
                logger.error(f"Путь {path} отсутствует в переменной PATH.")
                all_correct = False
            else:
                logger.info(f"Путь {path} найден в переменной PATH.")

        if all_correct:
            logger.info(f"### Все переменные Node.js локального окружения настроены корректно ###.")

        return all_correct
