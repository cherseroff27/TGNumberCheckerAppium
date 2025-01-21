import os
import shutil
import time

import subprocess

from LocalVariablesManager import LocalVariablesManager
from PackageManager import PackageManager
from InstallationStateManager import InstallationStateManager

from logger_config import Logger

logger = Logger.get_logger(__name__)


SDK_URL = "https://dl.google.com/android/repository/commandlinetools-win-9477386_latest.zip"
JAVA_URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.7%2B7/OpenJDK17U-jdk_x64_windows_hotspot_17.0.7_7.zip"


class AndroidToolManager:
    def __init__(self, base_project_dir, sdk_dir, java_dir, temp_files_dir):
        self.sdk_dir = sdk_dir
        self.java_dir = java_dir

        self.temp_files_dir = temp_files_dir

        self.package_manager = PackageManager()

        self.state_file_path = os.path.join(base_project_dir, "android_tools_installation_state.json")
        self.installation_state_manager = InstallationStateManager(self.state_file_path)


    def setup_all(self):
        """Комплексная установка всех компонентов."""
        self.initial_environment_setup()


    def initial_environment_setup(self):
        """Выполняет настройку локальных переменных среды для всех инструментов."""
        self._ensure_tool(setup_function=self.setup_java, tool_key="java_installed_path_key", env_var_name="JAVA_HOME", additional_paths=[os.path.join(self.java_dir, "bin")])
        self._ensure_tool(setup_function=self.setup_sdk, tool_key="sdk_installed_path_key", env_var_name="ANDROID_HOME", additional_paths=[os.path.join(self.sdk_dir, "cmdline-tools", "latest", "bin")])
        self._ensure_tool(setup_function=self.setup_sdk_manager, tool_key="sdkmanager_installed_path_key", env_var_name="SDK_MANAGER")
        self._ensure_tool(setup_function=self.setup_platform_tools, tool_key="platform_tools_installed_path_key", additional_paths=[os.path.join(self.sdk_dir, "platform-tools")])
        self._ensure_tool(setup_function=self.setup_emulator, tool_key="emulator_package_installed_path_key", additional_paths=[os.path.join(self.sdk_dir, "emulator")])
        self._ensure_tool(setup_function=self.setup_build_tools, tool_key="build_tools_installed_path_key", additional_paths=[os.path.join(self.sdk_dir, "build-tools", "34.0.0")])
        self._ensure_tool(setup_function=self.setup_hypervisor_driver, tool_key="hypervisor_driver_installed_path_key")


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


    def setup_java(self):
        """Устанавливает JDK локально и записывает пути в локальные переменные окружения."""
        logger.info("Скачиваем и настраиваем Java...")
        self.package_manager.reset_and_prepare_dir(self.java_dir)

        try:
            downloaded_archive_path = self.package_manager.download_tool("JDK", JAVA_URL, self.temp_files_dir)
            self.package_manager.unpack_tool(archive_path=downloaded_archive_path, target_dir=self.java_dir, extract_top_folder=False)

            java_home = self.java_dir
            if not java_home:
                raise Exception("Директория Java пуста после распаковки. Проверьте архив или URL установки.")

            LocalVariablesManager.add_to_local_env_var("JAVA_HOME", java_home)
            LocalVariablesManager.add_to_local_env_path_var(os.path.join(java_home, "bin"))
            self.installation_state_manager.add_installed_component("java_installed_path_key", java_home)
        except Exception as e:
            logger.error(f"Ошибка при установке Java: {e}")
            self.installation_state_manager.clear_state_file()
            raise


    def setup_sdk(self):
        """Устанавливает Android SDK Command-line tools и записывает пути в локальные переменные окружения."""
        logger.info("Скачиваем и настраиваем Android SDK Command-line tools...")
        self.package_manager.reset_and_prepare_dir(self.sdk_dir)
        try:
            downloaded_archive_path = self.package_manager.download_tool("SDK", SDK_URL, self.temp_files_dir)
            self.package_manager.unpack_tool(archive_path=downloaded_archive_path, target_dir=self.sdk_dir, extract_top_folder=True)

            sdk_contents = os.listdir(self.sdk_dir)   # Проверяем, есть ли файлы после извлечения
            if not sdk_contents:
                raise Exception("Директория SDK Command-line tools пуста после распаковки. Проверьте архив или URL установки.")

            cmdline_tools_dir = os.path.join(self.sdk_dir, "cmdline-tools")
            cmdline_tools = os.path.join(cmdline_tools_dir, "latest")

            if not os.path.exists(cmdline_tools):
                logger.info(f"Директория \"cmdline-tools\\latest\" не найдена. Распаковываем и перемещаем содержимое cmdline-tools...")
                os.makedirs(cmdline_tools, exist_ok=True)

                for item in os.listdir(cmdline_tools_dir):
                    item_path = os.path.join(cmdline_tools_dir, item)
                    if item != "latest":  # Исключаем только что созданную папку
                        shutil.move(item_path, cmdline_tools)

            sdkmanager_path = os.path.join(self.sdk_dir, "cmdline-tools", "latest", "bin", "sdkmanager.bat")
            if not os.path.exists(sdkmanager_path):
                raise Exception(f"sdkmanager.bat не найден по пути {sdkmanager_path}. Проверьте процесс распаковки...")

            logger.info("Принимаем все лицензии sdkmanager.bat...")
            subprocess.run([sdkmanager_path, "--licenses", "--verbose"], input="y\n" * 10, text=True, check=True)

            logger.info(f"Директория SDK Command-line tools: {cmdline_tools}")

            LocalVariablesManager.add_to_local_env_var("ANDROID_HOME", self.sdk_dir)
            LocalVariablesManager.add_to_local_env_path_var(os.path.join(cmdline_tools, "bin"))

            self.installation_state_manager.add_installed_component("sdk_installed_path_key", self.sdk_dir)
            self.installation_state_manager.add_installed_component("cmdline_tools_path_key", os.path.join(cmdline_tools, "bin"))

        except Exception as e:
            logger.error(f"Ошибка при установке Android SDK Command-line tools: {e}")
            self.installation_state_manager.clear_state_file()
            raise


    def setup_sdk_manager(self):
        """Устанавливает необходимые пакеты Android SDK и записывает пути в локальные переменные окружения."""
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        sdkmanager_path = os.path.join(android_home, "cmdline-tools", "latest", "bin", "sdkmanager.bat")
        if not os.path.exists(sdkmanager_path):
            raise Exception("sdkmanager.bat не найден. Убедитесь в том, что Android SDK Command-line tools корректно установлены.")

        logger.info("Устанавливаем пакет platforms;android-22 и системный образ system-images;android-22;google_apis;x86...")

        packages = [
            "platforms;android-22",
            "system-images;android-22;google_apis;x86",
        ]

        for package in packages:
            subprocess.run([sdkmanager_path, "--install", package, "--verbose"], check=True)

        LocalVariablesManager.add_to_local_env_var("SDK_MANAGER", sdkmanager_path)
        self.installation_state_manager.add_installed_component("sdkmanager_installed_path_key", sdkmanager_path)


    def setup_platform_tools(self):
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.installation_state_manager.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return
        try:
            sdkmanager_path = os.environ.get("SDK_MANAGER")
            if not os.path.exists(sdkmanager_path):
                raise Exception("sdkmanager.bat не найден. Убедитесь в том, что Android SDK Command-line tools корректно установлены.")

            subprocess.run([sdkmanager_path, "--install", "platform-tools", "--verbose"], check=True)

            logger.info("Добавляем platform-tools в глобальные переменные среды...")
            platform_tools_dir = os.path.join(android_home, "platform-tools")

            if os.path.exists(platform_tools_dir):
                logger.info("Добавляем platform-tools в локальные переменные окружения и в конфиг состояния установки")
                LocalVariablesManager.add_to_local_env_path_var(platform_tools_dir)

                self.installation_state_manager.add_installed_component("platform_tools_installed_path_key", platform_tools_dir)
            else:
                raise Exception("Platform-tools не найдены. Проверьте процесс установки.")

        except Exception as e:
            logger.error(f"Ошибка при установке platform-tools: {e}")
            self.installation_state_manager.clear_state_file()
            raise Exception("Произошла ошибка в ходе установки platform-tools. Проверьте процесс установки.")


    def setup_build_tools(self):
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.installation_state_manager.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        try:
            sdkmanager_path = os.environ.get("SDK_MANAGER")
            if not os.path.exists(sdkmanager_path):
                raise Exception("sdkmanager.bat не найден. Убедитесь в том, что Android SDK Command-line tools корректно установлены.")

            subprocess.run([sdkmanager_path, "--install", "build-tools;34.0.0", "--verbose"], check=True)

            logger.info("Добавляем build_tools в глобальные переменные среды...")
            build_tools_dir = os.path.join(android_home, "build-tools", "34.0.0")

            if os.path.exists(build_tools_dir):
                logger.info("Добавляем build-tools в локальные переменные окружения и в конфиг состояния установки")
                LocalVariablesManager.add_to_local_env_path_var(build_tools_dir)
                self.installation_state_manager.add_installed_component("build_tools_installed_path_key", build_tools_dir)
            else:
                raise Exception("Build_tools не найдены. Проверьте процесс установки.")

        except Exception as e:
            logger.error(f"Ошибка при установке build_tools: {e}")
            self.installation_state_manager.clear_state_file()
            raise Exception("Произошла ошибка в ходе установки build_tools. Проверьте процесс установки.")


    def setup_emulator(self):
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.installation_state_manager.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return
        try:
            sdkmanager_path = os.environ.get("SDK_MANAGER")
            if not os.path.exists(sdkmanager_path):
                raise Exception("sdkmanager.bat не найден. Убедитесь в том, что Android SDK корректно установлен.")

            subprocess.run([sdkmanager_path, "--install", "emulator", "--verbose"], check=True)

            emulator_dir = os.path.join(android_home, "emulator")

            if os.path.exists(emulator_dir):
                logger.info("Добавляем emulator в локальные переменные окружения и в конфиг состояния установки")
                LocalVariablesManager.add_to_local_env_path_var(emulator_dir)

                self.installation_state_manager.add_installed_component("emulator_package_installed_path_key", emulator_dir)
            else:
                raise Exception("Emulator не установлен. Проверьте процесс установки.")

        except Exception as e:
            logger.error(f"Ошибка при установке emulator: {e}")
            self.installation_state_manager.clear_state_file()
            raise Exception("Произошла ошибка в ходе установки emulator. Проверьте процесс установки.")

    def setup_hypervisor_driver(self):
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.installation_state_manager.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        sdkmanager_path = os.environ.get("SDK_MANAGER")
        if not os.path.exists(sdkmanager_path):
            raise Exception("sdkmanager.bat не найден. Убедитесь в том, что Android SDK корректно установлен.")

        packages = [
            "extras;google;Android_Emulator_Hypervisor_Driver",
            "extras;intel;Hardware_Accelerated_Execution_Manager",
        ]

        logger.info("Устанавливаем пакеты Hypervisor_Driver...")

        for package in packages:
            subprocess.run([sdkmanager_path, "--install", package, "--verbose"], check=True)

        logger.info("Проверяем наличие папки extras и драйверов внутри...")

        hypervisor_driver_intel_path = os.path.join(android_home, "extras", "intel")
        hypervisor_driver_google_path = os.path.join(android_home, "extras", "google")

        if os.path.exists(hypervisor_driver_intel_path) and os.path.exists(hypervisor_driver_google_path):
            if self.install_windows_hypervisor_driver():
                self.installation_state_manager.add_installed_component("hypervisor_driver_installed_path_key", hypervisor_driver_intel_path)
            else:
                logger.error("Не удалось установить hypervisor_driver. Проверьте процесс и порядок установки.")
        else:
            raise Exception("Папка extras с установщиками hypervisor_driver не найдена. Проверьте процесс и порядок установки.")


    def install_windows_hypervisor_driver(self):
        """
        Устанавливает драйверы для поддержки виртуализации на Windows:
        Intel HAXM или Android Emulator Hypervisor Driver.
        """
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.installation_state_manager.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена.")
            return

        aehd_driver_installer = os.path.join(android_home, "extras", "google", "Android_Emulator_Hypervisor_Driver", "silent_install.bat")
        haxm_installer = os.path.join(android_home, "extras", "intel", "Hardware_Accelerated_Execution_Manager", "silent_install.bat")

        try:
            if os.path.exists(aehd_driver_installer):
                logger.info("Удаляем Android Emulator Hypervisor Driver...")
                subprocess.run([aehd_driver_installer, "-u"], check=True, shell=True, capture_output=True, text=True)

                time.sleep(1)

                logger.info("Устанавливаем Android Emulator Hypervisor Driver...")
                subprocess.run(aehd_driver_installer, check=True, shell=True, capture_output=True, text=True)
            else:
                logger.error("Не найден установочный файл для Android Emulator Hypervisor Driver.")
                return False

            if os.path.exists(haxm_installer):
                logger.info("Устанавливаем Intel HAXM...")
                subprocess.run(haxm_installer, check=True)
            else:
                logger.error("Не найден установочный файл для HAXM")
                return False

            logger.info("Установка hypervisor_driver завершена успешно.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при установке hypervisor_driver: {e}")
            return False
        except Exception as e:
            logger.error(f"Непредвиденная ошибка: {e}")
            return False


    def restart_adb_server(self):
        android_home = os.environ.get("ANDROID_HOME")
        if not android_home:
            self.installation_state_manager.clear_state_file()
            logger.warning("Переменная среды ANDROID_HOME не установлена. Скорее всего platform-tools не установлены."
                           "Попробуйте переустановить Android SDK")
            return

        adb_path = os.path.join(android_home, "platform-tools", "adb.exe")

        logger.info(f"[Останавливаем ADB сервер...]")
        subprocess.run([adb_path, "kill-server"])

        logger.info(f"[Запускаем ADB сервер...]")
        subprocess.run([adb_path, "start-server"])

        logger.info(f"[ADB сервер запущен!]")


    def verify_sdk_tools_environment_setup(self):
        """
        Проверяет корректность установленных переменных среды и содержимого PATH.
        Returns: bool: True, если все переменные и пути корректны, иначе False.
        """

        variables_to_check = {
            "JAVA_HOME": self.java_dir,
            "ANDROID_HOME": self.sdk_dir,
            "SDK_MANAGER": os.path.join(self.sdk_dir, "cmdline-tools", "latest", "bin", "sdkmanager.bat")
        }

        paths_to_check = [
            os.path.join(self.java_dir, "bin"),
            os.path.join(self.sdk_dir, "cmdline-tools", "latest", "bin"),
            os.path.join(self.sdk_dir, "platform-tools"),
            os.path.join(self.sdk_dir, "build-tools", "34.0.0"),
            os.path.join(self.sdk_dir, "emulator")
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
            logger.info("### Все переменные SDK\\JDK локального окружения настроены корректно ###.")

        return all_correct


