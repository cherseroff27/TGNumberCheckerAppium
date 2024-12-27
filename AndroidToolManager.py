import ctypes

import os
import json
import shutil
import sys
import zipfile

import requests
import subprocess

import winreg

from tqdm import tqdm

from logger_config import Logger

logger = Logger.get_logger(__name__)

if hasattr(sys, 'frozen'):  # Программа запущена как .exe файл
    BASE_PROJECT_DIR = os.path.abspath(os.path.dirname(sys.executable))
else:  # Программа запущена как скрипт .py
    BASE_PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))

SDK_URL = "https://dl.google.com/android/repository/commandlinetools-win-9477386_latest.zip"
JAVA_URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.7%2B7/OpenJDK17U-jdk_x64_windows_hotspot_17.0.7_7.zip"


class AndroidToolManager:
    def __init__(self, tools_installation_dir):
        self.tools_dir = os.path.join(tools_installation_dir, "tools")
        self.sdk_dir = os.path.join(self.tools_dir, "SDK")
        self.java_dir = os.path.join(self.tools_dir, "JAVA")
        self.temp_files_dir = os.path.join(self.tools_dir, "TEMP_FILES")
        self.avd_devices_dir = os.path.join(self.tools_dir, "AVD_DEVICES")

        required_directories = [self.tools_dir, self.temp_files_dir, self.avd_devices_dir]
        for directory in required_directories:
            os.makedirs(directory, exist_ok=True)

        self.state_file_path = os.path.join(tools_installation_dir, "tools_installation_state.json")
        self.state = self.load_state()


    def clear_state_file(self):
        """
        Полностью очищает файл состояния, удаляя все данные.
        """
        if os.path.exists(self.state_file_path):
            logger.info(f"Очищаю файл состояния: {self.state_file_path}")
            with open(self.state_file_path, "w") as file:
                # Можно оставить пустой объект JSON или просто пустой файл
                file.write("{}")  # Записываем пустой JSON объект
            self.state = {}  # Очищаем текущее состояние в памяти
        else:
            logger.warning(f"Файл состояния {self.state_file_path} не существует. Очищать нечего.")


    def load_state(self):
        if os.path.exists(self.state_file_path):
            with open(self.state_file_path, "r") as file:
                return json.load(file)
        return {}


    # noinspection PyTypeChecker
    def save_state(self):
        with open(self.state_file_path, "w") as file:
            json.dump(self.state, file, indent=4)


    @staticmethod
    def reset_and_prepare_dir(directory):
        logger.info(f"Удаляю директорию и настраиваю заново: {directory}...")
        if os.path.exists(directory):
            shutil.rmtree(directory)


    def setup_java(self):
        """Устанавливает JDK локально."""
        if self.state.get("java_installed"):
            logger.info("Java уже установлена в глобальные переменные среды. Пропускаем установку.")
            return

        logger.info("Скачиваем и настраиваем Java...")
        self.reset_and_prepare_dir(self.java_dir)

        try:
            archive_path = self.download_tool("Java", JAVA_URL, self.temp_files_dir)
            self.unpack_tool(archive_path, self.java_dir)

            java_contents = os.listdir(self.java_dir)   # Проверяем, есть ли файлы после извлечения
            if not java_contents:
                raise Exception("Java directory is empty after extraction. Check the archive or URL.")

            java_home = os.path.join(self.java_dir, java_contents[0])  # Предполагается структура JDK

            self.add_to_system_variable("JAVA_HOME", java_home)
            self.add_to_system_path(os.path.join(java_home, "bin"))
            self.state["java_installed"] = True
            self.save_state()
        except Exception as e:
            logger.error(f"Ошибка при установке Java: {e}")
            self.clear_state_file()
            raise

    def setup_sdk(self):
        """Устанавливает SDK Command-line tools."""
        if self.state.get("sdk_installed"):
            logger.info("SDK уже установлена в глобальные переменные среды. Пропускаем установку.")
            return

        logger.info("Скачиваем и настраиваем Android SDK...")
        self.reset_and_prepare_dir(self.sdk_dir)

        archive_path = self.download_tool("SDK", SDK_URL, self.temp_files_dir)
        self.unpack_tool(archive_path, self.sdk_dir)

        sdk_contents = os.listdir(self.sdk_dir)   # Проверяем, есть ли файлы после извлечения
        if not sdk_contents:
            raise Exception("SDK Command-line tools directory is empty after extraction. Check the archive or URL.")

        cmdline_tools_dir = os.path.join(self.sdk_dir, "cmdline-tools")
        cmdline_tools = os.path.join(cmdline_tools_dir, "latest")

        if not os.path.exists(cmdline_tools):
            logger.info(f"'latest' directory not found. Creating it and moving cmdline-tools contents...")
            os.makedirs(cmdline_tools, exist_ok=True)

            for item in os.listdir(cmdline_tools_dir):
                item_path = os.path.join(cmdline_tools_dir, item)
                if item != "latest":  # Исключаем только что созданную папку
                    shutil.move(item_path, cmdline_tools)

        sdkmanager_path = os.path.join(self.sdk_dir, "cmdline-tools", "latest", "bin", "sdkmanager.bat")
        if not os.path.exists(sdkmanager_path):
            raise Exception(f"sdkmanager.bat not found at {sdkmanager_path}. Check the extraction process.")

        logger.info(f"SDK Command-line tools directory: {cmdline_tools}")

        self.add_to_system_variable("ANDROID_HOME", self.sdk_dir)
        self.add_to_system_path(os.path.join(cmdline_tools, "bin"))
        self.add_to_system_path(os.path.join(self.sdk_dir, "platform-tools"))
        self.state["sdk_installed"] = True
        self.save_state()


    def install_sdk_packages(self):
        """Устанавливает необходимые пакеты Android SDK."""
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        if self.state.get("sdk_packages_installed"):
            logger.warning("SDK пакеты уже установлены. Пропускаем установку.")
            return

        sdkmanager_path = os.path.join(android_home, "cmdline-tools", "latest", "bin", "sdkmanager.bat")
        if not os.path.exists(sdkmanager_path):
            raise Exception("sdkmanager.bat not found. Ensure SDK is set up correctly.")

        packages = [
            "platform-tools",
            "platforms;android-22",
            "system-images;android-22;google_apis;x86",
            "emulator",
            "build-tools;34.0.0"
        ]

        logger.info("Принимаем все лицензии...")
        try:
            subprocess.run([sdkmanager_path, "--licenses", "--verbose"], input="y\n" * 10, text=True, check=True)

            for package in packages:
                logger.info(f"Устанавливаем пакет: {package}")
                # Установка пакета с автоматическим подтверждением
                subprocess.run([sdkmanager_path, "--install", package, "--verbose"], check=True)
                # После успешной установки обновляем состояние
                self.state["sdk_packages_installed"] = True
                self.save_state()
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при установке пакетов SDK: {e}")


    def setup_build_tools(self):
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        if self.state.get("build_tools_installed"):
            logger.warning("Build-tools уже настроены. Пропускаем настройку.")
            return

        logger.info("Добавляем build_tools в глобальные переменные среды...")
        build_tools_dir = os.path.join(android_home, "build-tools", "34.0.0")
        if os.path.exists(build_tools_dir):
            logger.info("Настраиваем Build-tools...")
            self.add_to_system_path(build_tools_dir)

            self.state["build_tools_installed"] = True
            self.save_state()
        else:
            raise Exception("Build-tools не найдены. Проверьте процесс установки.")


    def setup_emulator(self):
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        if self.state.get("emulator_installed"):
            logger.info("Эмулятор уже настроен. Пропускаем настройку.")
            return

        logger.info("Добавляем emulator в глобальные переменные среды...")

        emulator_path = os.path.join(android_home, "emulator")

        if os.path.exists(emulator_path):
            self.add_to_system_path(emulator_path)
            self.state["emulator_installed"] = True
            self.save_state()
        else:
            raise Exception("Эмулятор не установлен. Проверьте процесс установки.")


    @staticmethod
    def download_tool(filename, url, target_dir):
        """Загружает файл с отображением прогресса."""
        os.makedirs(target_dir, exist_ok=True)  # Создаем директорию, если её нет
        archive_path = os.path.join(target_dir, f"{filename}_temp.zip")

        # Если файл уже существует, пропускаем загрузку
        if os.path.exists(archive_path):
            logger.info(f"Файл {filename} уже существует в кэше: {archive_path}. Пропускаем загрузку.")
            return archive_path

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))  # Получаем общий размер файла
            chunk_size = 8192  # Размер блока данных

            with open(archive_path, "wb") as file, tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"Downloading {filename}",
                    colour="green"
            ) as progress_bar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    file.write(chunk)
                    progress_bar.update(len(chunk))  # Обновляем прогресс-бар

            return archive_path
        else:
            raise Exception(f"Не удалось скачать файл {filename} с {url}. Status code: {response.status_code}")


    def clear_tools_files_cache(self):
        """Удаляет все временные файлы из директории TEMP_FILES и выводит их названия в лог."""
        if os.path.exists(self.temp_files_dir):
            logger.info(f"Начинаем удаление закэшированных файлов из {self.temp_files_dir}...")

            # Получаем список всех файлов в директории
            for filename in os.listdir(self.temp_files_dir):
                file_path = os.path.join(self.temp_files_dir, filename)

                # Проверяем, что это файл (а не директория)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)  # Удаляем файл
                        logger.info(f"Удален файл: {filename}")  # Логируем удаление
                    except Exception as e:
                        logger.error(f"Ошибка при удалении файла {filename}: {e}")

            # После удаления всех файлов можем очистить директорию
            # если нужно восстановить структуру директории
            os.makedirs(self.temp_files_dir, exist_ok=True)

            logger.info("Закэшированные файлы успешно удалены.")
        else:
            logger.warning(f"Директория {self.temp_files_dir} отсутствует. Нечего удалять.")


    @staticmethod
    def unpack_tool(archive_path, target_dir):
        logger.info(f"Распаковываем архив {archive_path} в {target_dir}...")
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(target_dir)


    @staticmethod
    def add_to_system_path(new_path):
        """Добавляет путь в системную переменную PATH и уведомляет систему об изменении (Windows)."""
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            current_path, _ = winreg.QueryValueEx(key, "Path")
            if new_path not in current_path:
                new_path_value = f"{current_path};{new_path}"
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path_value)
                logger.info(f"Добавлен в системный PATH: {new_path}")
        AndroidToolManager.notify_environment_change()


    @staticmethod
    def add_to_system_variable(variable_name, value):
        """Устанавливает системную переменную и уведомляет систему об изменении (только для Windows)."""
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, variable_name, 0, winreg.REG_EXPAND_SZ, value)
            logger.info(f"Установлена системная переменная {variable_name}: {value}")
        AndroidToolManager.notify_environment_change()


    def remove_paths_from_system(self):
        """
        Удаляет все пути, добавленные этим скриптом, из переменных среды,
        и удаляет конфигурационный файл с состоянием установленных компонентов.
        """
        java_home = os.environ.get("JAVA_HOME")
        if not java_home:
            self.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        self.clear_state_file()

        # Пути, которые были добавлены в PATH, согласно verify_environment_setup
        paths_to_remove = [
            os.path.join(java_home, "jdk-17.0.7+7", "bin"),
            os.path.join(android_home, "cmdline-tools", "latest", "bin"),
            os.path.join(android_home, "platform-tools"),
            os.path.join(android_home, "build-tools", "34.0.0"),
            os.path.join(android_home, "emulator"),
        ]

        try:
            with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                    0, winreg.KEY_READ | winreg.KEY_WRITE
            ) as key:
                current_path, _ = winreg.QueryValueEx(key, "Path")
                current_paths = current_path.split(";")

                # Удаляем пути, которые добавлялись этим скриптом
                new_paths = [path for path in current_paths if path not in paths_to_remove]
                new_path_value = ";".join(new_paths)

                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path_value)
                logger.info(f"Удалены пути, добавленные скриптом, из переменной PATH.")
                AndroidToolManager.notify_environment_change()

                # Удаляем системные переменные JAVA_HOME и ANDROID_HOME
                env_vars_to_remove = ["JAVA_HOME", "ANDROID_HOME"]
                for var in env_vars_to_remove:
                    try:
                        winreg.DeleteValue(key, var)
                        logger.info(f"Переменная {var} удалена.")
                        AndroidToolManager.notify_environment_change()
                    except FileNotFoundError:
                        logger.warning(f"Переменная {var} не найдена, пропускаем.")
                    except Exception as e:
                        logger.error(f"Ошибка при удалении {var}: {e}")

        except FileNotFoundError:
            logger.warning("Ключ реестра не найден. Удаление переменных невозможно.")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при доступе к реестру: {e}")


    def verify_environment_setup(self):
        """Проверяет наличие необходимых компонентов и их корректную настройку в системных переменных."""
        logger.info("Проверка установленной среды...")

        java_home = os.environ.get("JAVA_HOME")
        if not java_home:
            self.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        # Проверяем пути, которые должны существовать
        paths_to_check = {
            "Java (bin)": os.path.join(java_home, "jdk-17.0.7+7", "bin"),
            "SDK (cmdline-tools/bin)": os.path.join(android_home, "cmdline-tools", "latest", "bin"),
            "SDK (build-tools)": os.path.join(android_home, "build-tools", "34.0.0"),
            "SDK (platform-tools)": os.path.join(android_home, "platform-tools"),
            "SDK (emulator)": os.path.join(android_home, "emulator"),
        }

        all_paths_exist = True
        for description, path in paths_to_check.items():
            if os.path.exists(path):
                logger.info(f"{description} найден: {path}")
            else:
                logger.warning(f"{description} отсутствует: {path}")
                all_paths_exist = False


        # Проверяем системные переменные среды
        env_vars_to_check = {
            "JAVA_HOME": java_home,
            "ANDROID_HOME": android_home,
        }

        all_env_vars_set = True
        for var, expected_value in env_vars_to_check.items():
            actual_value = os.environ.get(var)
            if actual_value and os.path.abspath(actual_value) == os.path.abspath(expected_value):
                logger.info(f"Переменная среды {var} установлена корректно: {actual_value}")
            else:
                logger.warning(
                    f"Переменная среды {var} отсутствует или имеет некорректное значение. "
                    f"Ожидаемое: {expected_value}, текущее: {actual_value}"
                )
                all_env_vars_set = False

        # Проверяем наличие путей в системной переменной PATH
        path_dirs = os.environ.get("PATH", "").split(";")
        paths_to_check_in_path = [os.path.join(java_home, "jdk-17.0.7+7", "bin"),
                                  os.path.join(android_home, "cmdline-tools", "latest", "bin"),
                                  os.path.join(android_home, "platform-tools"),
                                  os.path.join(android_home, "build-tools", "34.0.0"),
                                  os.path.join(android_home, "emulator")]

        all_paths_in_path = True
        for path in paths_to_check_in_path:
            if any(os.path.abspath(path) == os.path.abspath(p) for p in path_dirs):
                logger.info(f"Путь {path} присутствует в PATH.")
            else:
                logger.warning(f"Путь {path} отсутствует в PATH.")
                all_paths_in_path = False

        # Итоговая проверка
        if all_paths_exist and all_env_vars_set and all_paths_in_path:
            logger.info("Все необходимые компоненты установлены и настроены корректно.")
            return True
        else:
            logger.error("Обнаружены проблемы с установкой и настройкой среды. Проверьте предупреждения выше.")
            return False


    @staticmethod
    def notify_environment_change():
        """Отправляет сообщение WM_SETTINGCHANGE для немедленного применения изменений переменных среды."""
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x1A

        result = ctypes.windll.user32.SendMessageTimeoutA(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            ctypes.cast(ctypes.c_char_p(b"Environment"), ctypes.POINTER(ctypes.c_char)),
            0,
            5000,  # Таймаут 5 секунд
            None
        )
        if result == 0:
            logger.warning("Не удалось отправить сообщение WM_SETTINGCHANGE. Переменные среды могут примениться с задержкой.")
        else:
            logger.info("Изменения переменных среды применены немедленно.")



    def check_tools(self):
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        tools = {
            "sdkmanager.bat": os.path.join(android_home, "cmdline-tools", "latest", "bin", "sdkmanager.bat"),
            "adb": os.path.join(android_home, "platform-tools", "adb.exe"),
        }

        for tool_name, tool_path in tools.items():
            if os.path.exists(tool_path):
                logger.info(f"Компонент {tool_name} найден по пути {tool_path}.")
                if tool_name != "sdkmanager.bat":
                    try:
                        subprocess.run([tool_path, "--version"], check=True, capture_output=True, text=True)
                        logger.info(f"Версия {tool_name} проверена.")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Ошибка при проверке версии {tool_name}: {e}")
            else:
                logger.error(f"{tool_name} не найден по пути {tool_path}. Проверьте установку.")


    def setup_java_and_sdk(self):
        self.setup_java()
        self.setup_sdk()


    def setup_sdk_packages(self):
        self.install_sdk_packages()


    def setup_build_tools_and_emulator(self):
        self.setup_build_tools()
        self.setup_emulator()
        self.check_tools()
