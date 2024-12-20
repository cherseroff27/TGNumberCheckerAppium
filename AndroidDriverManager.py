import os
import requests
from appium import webdriver
from appium.options.android import UiAutomator2Options
from EmulatorAuthConfigManager import EmulatorAuthConfigManager
import time
import socket
import logging
import threading
import subprocess

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

lock = threading.Lock()

class AndroidDriverManager:
    def __init__(self, local_ip: str, port: int, emulator_auth_config_manager: EmulatorAuthConfigManager):
        self.local_ip = local_ip
        self.port = port
        self.emulator_auth_config_manager = emulator_auth_config_manager
        self.driver = None
        self.process = None


    @staticmethod
    def execute_adb_command(command):
        thread_name = threading.current_thread().name

        with lock:
            try:
                result = subprocess.run(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                return result.stdout.strip()
            except Exception as e:
                logging.error(f"[{thread_name}] Ошибка при выполнении команды: {command}. {e}")
                return ""


    @staticmethod
    def is_port_free(port):
        """
        Проверяет, свободен ли порт.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return True
            except OSError:
                return False


    @staticmethod
    def free_port(port):
        """
        Освобождает занятый порт (только для Windows и Unix-подобных систем).
        """
        thread_name = threading.current_thread().name

        try:
            if os.name == 'nt':  # Windows
                command = f"netstat -ano | findstr :{port}"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    pids = [line.split()[-1] for line in result.stdout.strip().splitlines()]
                    for pid in pids:
                        subprocess.run(f"taskkill /PID {pid} /F", shell=True)
                    logging.info(f"[{thread_name}] Порт {port} успешно освобождён.")
                else:
                    logging.info(f"[{thread_name}] Порт {port} уже свободен.")
            else:  # Unix-like systems
                command = f"lsof -t -i:{port}"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    pids = result.stdout.strip().splitlines()
                    for pid in pids:
                        subprocess.run(f"kill -9 {pid.strip()}", shell=True)
                    logging.info(f"[{thread_name}] Порт {port} успешно освобождён.")
                else:
                    logging.info(f"[{thread_name}] Порт {port} уже свободен.")
        except Exception as e:
            logging.warning(f"[{thread_name}] Ошибка при освобождении порта {port}: {e}")


    def ensure_port_available(self):
        """
        Проверяет доступность порта и освобождает его, если необходимо.
        """
        thread_name = threading.current_thread().name

        while not self.is_port_free(self.port):
            logging.warning(f"[{thread_name}] Порт {self.port} занят. Попытка освобождения...")
            self.free_port(self.port)

            if not self.is_port_free(self.port):
                logging.error(f"[{thread_name}] Порт {self.port} не удалось освободить. Проверьте вручную.")
                return

        logging.error(f"[{thread_name}] Порт {self.port} свободен!")


    def start_appium_server(self):
        """
        Запускает сервер Appium на указанном порту.
        """
        thread_name = threading.current_thread().name

        with lock:
            self.ensure_port_available()

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
                logging.info(f"[{thread_name}] Appium сервер запущен на порту {self.port}.")
                time.sleep(3)  # Ждём несколько секунд для инициализации сервера
            except Exception as e:
                logging.error(f"[{thread_name}] Не удалось запустить Appium сервер на порту {self.port}: {e}")
                self.process = None


    @staticmethod
    def is_appium_server_running(url):
        try:
            response = requests.get(url + "/status")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


    @staticmethod
    def get_ui_automator2_options(device_name, platform_version, emulator_port):
        options = UiAutomator2Options()
        options.deviceName = device_name
        options.udid = f"emulator-{emulator_port}"
        options.platformVersion = platform_version

        options.platformName = "Android"
        options.automationName = "UiAutomator2"
        options.ignoreUnimportantViews = True
        options.disableWindowAnimation = True
        options.noReset = True

        return options


    def create_driver(self, avd_name, emulator_port, platform_version: str="9"):
        thread_name = threading.current_thread().name

        appium_server_url = f"http://{self.local_ip}:{self.port}"

        if not self.is_appium_server_running(appium_server_url):
            raise RuntimeError(f"[{thread_name}] Appium сервер на {appium_server_url} не запущен.")

        # Проверяем подключение эмулятора через ADB
        if not self.is_device_connected_adb(emulator_port):
            raise RuntimeError(f"[{thread_name}] Устройство emulator-{emulator_port} не подключено через ADB.")

        options = self.get_ui_automator2_options(avd_name, platform_version, emulator_port)

        try:
            logging.info(f"[{thread_name}] Создаём драйвер для {avd_name} на emulator-{emulator_port} через {appium_server_url}")
            self.driver = webdriver.Remote(command_executor=appium_server_url, options=options)


            return self.driver
        except Exception as e:
            print(f"[{thread_name}] Ошибка при создании драйвера: {e}")


    def is_device_connected_adb(self, emulator_port):
        """
        Проверяет, подключен ли эмулятор на указанном порту через ADB.
        """
        thread_name = threading.current_thread().name
        device_id = f"emulator-{emulator_port}"


        logging.info(f"[{thread_name}] Проверка подключения устройства {device_id} через ADB...")
        adb_output = self.execute_adb_command("adb devices")
        connected_devices = [
            line.split()[0] for line in adb_output.splitlines() if "device" in line
        ]

        if device_id in connected_devices:
            logging.info(f"[{thread_name}] Устройство {device_id} подключено.")
            return True
        else:
            logging.warning(f"[{thread_name}] Устройство {device_id} не подключено.")
            return False


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
        thread_name = threading.current_thread().name

        if self.process:
            self.process.terminate()
            self.process.wait()
            logging.info(f"[{thread_name}] Appium сервер на порту {self.port} остановлен.")
            self.process = None