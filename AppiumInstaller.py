import subprocess
import time
import os
import re

from LocalVariablesManager import LocalVariablesManager
from PackageManager import PackageManager

from logger_config import Logger
logger = Logger.get_logger(__name__)


class AppiumInstaller:
    def __init__(self, node_dir):
        """
        Инициализация путей и команд для локальной установки.
        """
        self.npm_command = "npm"
        self.appium_command = "appium"

        self.node_dir = node_dir

        self.local_variables_manager = LocalVariablesManager()
        self.package_manager = PackageManager()


    def fetch_appium_version(self):
        """ Проверяет, установлен ли Appium. """
        return self.package_manager.fetch_package_version("appium")


    def is_uiautomator2_driver_installed(self):
        """ Проверяет, установлен ли UIAutomator2 driver. """
        command = [self.appium_command, "driver", "list"]
        uiautomator2_driver_package_name = "uiautomator2"
        return self.package_manager.is_package_installed(command, uiautomator2_driver_package_name)


    def install_uiautomator2_driver(self):
        """
        Устанавливает или обновляет драйвер UIAutomator2.
        """
        try:
            logger.info("Проверка состояния драйвера UIAutomator2...")
            result = subprocess.run(
                [self.appium_command, "driver", "list", "--installed"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.info(f"Результат команды: {result.stdout}")

            if re.search(r"uiautomator2", result.stdout, re.IGNORECASE):
                logger.info("Драйвер UIAutomator2 уже установлен. Выполняется обновление...")
                subprocess.check_call(
                    [self.appium_command, "driver", "update", "uiautomator2"],
                    text=True,
                    shell=True
                )
                logger.info("Драйвер UIAutomator2 успешно обновлён.")
            else:
                logger.info("Установка драйвера UIAutomator2...")
                subprocess.check_call(
                    [self.appium_command, "driver", "install", "uiautomator2"],
                    text=True,
                    shell=True
                )
                logger.info("Драйвер UIAutomator2 успешно установлен.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка установки/обновления драйвера UIAutomator2: {e}")
            raise RuntimeError(f"Ошибка установки/обновления драйвера UIAutomator2: {e}")


    def install_appium(self):
        """
        Устанавливает Appium в локальную директорию.
        """
        if not self.package_manager.check_command_availability(self.appium_command):
            logger.info("Appium не найден. Выполняется установка...")
            logger.info(f"Запускаю команду: {self.npm_command} install -g appium")
            try:
                subprocess.check_call(
                    [self.npm_command, "install", "-g", "appium"],
                    text=True,
                    shell=True
                )
                logger.info("Appium успешно установлен.")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Ошибка установки Appium: {e}")


    def setup_appium_and_uiautomator2(self):
        """
        Основной метод для проверки и установки Appium и его зависимостей.
        """
        logger.info("Проверка наличия необходимых компонентов...")

        adb_package_name = "adb"
        if not self.package_manager.fetch_package_version(adb_package_name):
            raise RuntimeError("adb не установлен. Убедитесь, что он доступен.")

        node_path = "node"
        npm_path = "npm"

        self.package_manager.check_tool_availability(node_path)
        self.package_manager.check_tool_availability(npm_path)

        if not self.package_manager.fetch_package_version(node_path):
            raise RuntimeError("Node.js не установлен. Установите его перед запуском.")

        if not self.package_manager.fetch_package_version(npm_path):
            raise RuntimeError("npm не установлен. Убедитесь, что он доступен.")

        if self.fetch_appium_version() is None:
            logger.info("Appium или драйвер uiautomator2 не установлены. Выполняется установка...")
            self.install_appium()
            self.install_uiautomator2_driver()
            logger.info("Установка завершена.")
        else:
            logger.info("Appium и драйвер uiautomator2 уже установлены. Установка не требуется.")


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