from appium import webdriver
from appium.options.android import UiAutomator2Options
import subprocess
import time
import logging
import threading

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)



class AndroidDriverManager:
    def __init__(self, local_ip="127.0.0.1", port=4723, telegram_app_package=None):
        self.local_ip = local_ip
        self.port = port
        self.telegram_app_package = telegram_app_package
        self.driver = None
        self.process = None



    def start_appium_server(self):
        """
        Запускает сервер Appium на указанном порту.
        """

        log_filename = f"appium_server_{self.port}.log"  # Уникальное имя файла логов для каждого порта
        log_file = open(log_filename, "w")  # Открыть файл для записи логов

        command = f"appium --port {self.port} --log-level info"
        try:
            self.process = subprocess.Popen(
                command,
                shell=True,
                stdout=log_file,
                stderr=subprocess.STDOUT  # Перенаправить stderr в stdout
            )
            logging.info(f"Appium сервер запущен на порту {self.port}.")
            time.sleep(5)  # Ждём несколько секунд для инициализации сервера
        except Exception as e:
            logging.error(f"Не удалось запустить Appium сервер на порту {self.port}: {e}")
            self.process = None


    def get_ui_automator2_options(self, device_name, platform_version):
        options = UiAutomator2Options()
        options.deviceName = device_name
        options.platformVersion = platform_version

        options.platformName = "Android"
        options.automationName = "UiAutomator2"
        options.platformVersion = "11"
        options.ignoreUnimportantViews = True
        options.disableWindowAnimation = True
        options.appPackage = self.telegram_app_package
        options.noReset = True

        return options


    def create_driver(self, device_name, platform_version="11"):
        appium_server_url = f"http://{self.local_ip}:{self.port}"

        options = self.get_ui_automator2_options(device_name, platform_version)

        try:
            self.driver = webdriver.Remote(command_executor=appium_server_url, options=options)

            return self.driver
        except Exception as e:
            print(f"Ошибка при создании драйвера: {e}")


    @staticmethod
    def execute_adb_command(command):
        try:
            result = subprocess.run(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return result.stdout.strip()
        except Exception as e:
            print(f"Ошибка при выполнении команды: {command}. {e}")
            return ""


    def ensure_adb_connection(self):
        command = f"adb.exe connect {self.local_ip}:{self.port}"
        self.execute_adb_command(command)


    def stop_driver(self):
        if self.driver:
            self.driver.quit()


    def stop_appium_server(self):
        """
        Останавливает сервер Appium.
        """
        if self.process:
            self.process.terminate()
            self.process.wait()
            logging.info(f"[{threading.current_thread().name}] Appium сервер на порту {self.port} остановлен.")
            self.process = None