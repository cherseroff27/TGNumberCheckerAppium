import subprocess
import time
import os
import re

from InstallationStateManager import InstallationStateManager
from PackageManager import PackageManager

from logger_config import Logger
logger = Logger.get_logger(__name__)


class AppiumInstaller:
    def __init__(self, base_project_dir):
        """
        Инициализация путей и команд для локальной установки.
        """
        self.node_command = "node"
        self.npm_command = "npm"
        self.appium_command = "appium"

        self.package_manager = PackageManager()

        self.state_file_path = os.path.join(base_project_dir, "appium_tools_installation_state.json")
        self.installation_state_manager = InstallationStateManager(self.state_file_path)


    def setup_all(self):
        """Комплексная установка всех компонентов."""
        self.initial_environment_setup()


    def initial_environment_setup(self):
        """Выполняет настройку локальных переменных среды для всех инструментов."""
        logger.info("Проверка наличия необходимых компонентов...")

        if not self.package_manager.fetch_package_version(self.node_command):
            raise RuntimeError("Node.js не установлен. Установите его перед запуском.")

        if not self.package_manager.fetch_package_version(self.npm_command):
            raise RuntimeError("Npm не установлен. Убедитесь, что он доступен.")

        self._ensure_tool(
            setup_function=self.install_appium,
            tool_key="appium_installed_path_key",
        )
        self._ensure_tool(
            setup_function=self.install_uiautomator2_driver,
            tool_key="uiautomator2_driver_installed_path_key",
        )


    def _ensure_tool(self, setup_function, tool_key):
        """Убедиться, что инструмент установлен, и при необходимости выполнить установку."""
        if not self._load_tool(tool_key):
            setup_function()


    def _load_tool(self, tool_key):
        """Загружает инструмент из состояния или выполняет установку."""
        is_tool_installed = self.installation_state_manager.get_installed_component_flag(tool_key)

        if not is_tool_installed:
            logger.info(f"Инструмент '{tool_key}' имеет флаг установки {is_tool_installed}, требуется установка. Начинаем установку...")
            self.installation_state_manager.remove_installed_component(tool_key)
            return False

        logger.info(f"Флаг установки инструмента '{tool_key}': {is_tool_installed}")
        return True


    def fetch_appium_version(self):
        """ Проверяет, установлен ли Appium. """
        return self.package_manager.fetch_package_version("appium")


    def is_uiautomator2_driver_installed(self):
        """ Проверяет, установлен ли UIAutomator2 driver. """
        try:
            logger.info("Проверка состояния драйвера UIAutomator2...")
            result = subprocess.run(
                [self.appium_command, "driver", "list", "--installed"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
            )

            # Логирование вывода
            logger.info("STDOUT:" + result.stdout)
            logger.info("STDERR:" + result.stderr)

            if re.search(r"uiautomator2", result.stdout, re.IGNORECASE) or re.search(r"uiautomator2", result.stderr, re.IGNORECASE):
                return True
            else:
                return False

        except Exception as e:
            raise RuntimeError(f"Ошибка проверки наличия UIAutomator2 driver: {e}")


    def install_uiautomator2_driver(self):
        """
        Устанавливает или обновляет драйвер UIAutomator2.
        """
        if not self.is_uiautomator2_driver_installed():
            self.installation_state_manager.remove_installed_component("uiautomator2_driver_installed_path_key")

            try:
                logger.info("Драйвер UIAutomator2 еще НЕ установлен. Требуется установка...")
                result = subprocess.run(
                    [self.appium_command, "driver", "install", "uiautomator2"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=True
                )

                # Логирование вывода
                logger.info("STDOUT:" + result.stdout)
                logger.info("STDERR:" + result.stderr)

                logger.info("Драйвер UIAutomator2 успешно установлен.")

                self.installation_state_manager.add_installed_component_by_flag("uiautomator2_driver_installed_path_key", True)
            except Exception as e:
                raise RuntimeError(f"Ошибка установки драйвера UIAutomator2: {e}")
        else:
            logger.info("Драйвер Uiautomator2 уже установлен. Установка не требуется.")
            self.installation_state_manager.add_installed_component_by_flag("uiautomator2_driver_installed_path_key", True)


    def install_appium(self):
        """
        Устанавливает Appium в локальную директорию.
        """
        if not self.fetch_appium_version():
            self.installation_state_manager.remove_installed_component("appium_installed_path_key")

            logger.info(f"Запускаю команду: {self.npm_command} install -g appium")
            try:
                result = subprocess.run(
                    [self.npm_command, "install", "-g", "appium"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=True
                )

                # Логирование вывода
                logger.info("STDOUT:" + result.stdout)
                logger.info("STDERR:" + result.stderr)

                logger.info("Appium успешно установлен.")

                self.installation_state_manager.add_installed_component_by_flag("appium_installed_path_key", True)

            except Exception as e:
                raise RuntimeError(f"Ошибка установки Appium: {e}")

        else:
            logger.info("Appium уже установлен. Установка не требуется.")
            self.installation_state_manager.add_installed_component_by_flag("appium_installed_path_key", True)


    def are_required_flags_set(self):
        """
        Проверяет, установлены ли флаги для ключей appium_installed_path_key и
        uiautomator2_driver_installed_path_key в True.

        :return: True, если оба флага установлены в True. False в противном случае.
        """
        appium_flag = self.installation_state_manager.get_installed_component_flag("appium_installed_path_key")
        uiautomator2_flag = self.installation_state_manager.get_installed_component_flag("uiautomator2_driver_installed_path_key")

        if appium_flag and uiautomator2_flag:
            logger.info("Все необходимые флаги установлены в True.")
            return True
        else:
            logger.warning(
                "Не все необходимые флаги установлены:\n"
                f"appium_installed_path_key={appium_flag}\n, "
                f"uiautomator2_driver_installed_path_key={uiautomator2_flag}."
            )
            return False


class AppiumServerController:
    def __init__(self):
        """
        Инициализирует контроллер сервера Appium.
        """
        self.appium_command = "appium"
        self.server_process = None


    def start_server(self, host="127.0.0.1", port=4723, log_file="appium_server.log"):
        """
        Запускает сервер Appium.
        :param host: Хост для сервера.
        :param port: Порт для сервера.
        :param log_file: Путь к лог-файлу.
        """
        if self.server_process:
            logger.info("Сервер Appium уже запущен.")
            return

        logger.info("Запуск сервера Appium...")
        log_file_path = os.path.abspath(log_file)
        with open(log_file_path, "w") as log:
            self.server_process = subprocess.Popen(
                [self.appium_command, "--address", host, "--port", str(port)],
                stdout=log,
                stderr=log,
                shell=True,
                text=True
            )
        logger.info(f"Сервер Appium запущен на {host}:{port}. Логи: {log_file_path}")
        time.sleep(3)  # Ждем инициализацию сервера


    def stop_server(self):
        """
        Останавливает сервер Appium.
        """
        if self.server_process and self.server_process.poll() is None:
            logger.info("Остановка сервера Appium...")
            self.server_process.terminate()
            self.server_process.wait()
            logger.info("Сервер Appium остановлен.")
        else:
            logger.info("Сервер Appium не запущен.")
        self.server_process = None