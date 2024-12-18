import os
import subprocess
import sys
import threading
import time
import logging

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


class EmulatorManager:
    def __init__(self):
        self.lock = threading.Lock()


    @staticmethod
    def update_progress(progress, total, message=""):
        """
        Обновляет строку прогресса в терминале.
        :param progress: Текущий прогресс (например, количество завершённых шагов)
        :param total: Общее количество шагов
        :param message: Сообщение, которое будет отображаться
        """
        percent = int((progress / total) * 100)
        bar = f"[{'#' * (percent // 2)}{'-' * (50 - (percent // 2))}] {percent}%"
        sys.stdout.write(f"\r{message} {bar} {progress}/{total}")
        sys.stdout.flush()


    def _execute_command(self, command):
        """
        Выполняет системную команду с обработкой ошибок.
        """
        thread_name = threading.current_thread().name
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logging.error(f"[{thread_name}] Command failed: {command}\nError: {result.stderr}")
                return None
        except Exception as e:
            logging.error(f"[{thread_name}] Failed to execute command: {command}\nException: {e}")
            return None


    def _check_if_emulator_exists(self, avd_name):
        """
        Проверяет, существует ли эмулятор с указанным именем.
        """
        thread_name = threading.current_thread().name
        command = "emulator -list-avds"
        avd_list = self._execute_command(command)
        if avd_list:
            if avd_name in avd_list.split():
                logging.info(f"[{thread_name}] Эмулятор {avd_name} существует.")
                return True
            else:
                logging.info(f"[{thread_name}] Эмулятор {avd_name} отсутствует в списке AVD.")
                return False
        else:
            logging.error(f"[{thread_name}] Не удалось получить список AVD. Команда вернула пустой результат.")
            return False


    def _create_emulator(self, avd_name, system_image):
        """
        Создаёт новый эмулятор и с указанным образом.
        """
        thread_name = threading.current_thread().name
        logging.info(f"[{thread_name}] Создание эмулятора {avd_name} с образом {system_image}...")
        create_command = (
            f"avdmanager create avd -n {avd_name} -k \"{system_image}\" --device \"pixel\" --force"
        )

        result = self._execute_command(create_command)

        if result is not None:
            logging.info(f"[{thread_name}] Эмулятор {avd_name} успешно .")
            return True
        else:
            logging.error(f"[{thread_name}] Не удалось создать эмулятор {avd_name}.")
            return False


    def _get_installed_packages(self):
        """
        Возвращает список доступных пакетов из вывода команды 'sdkmanager --list'.
        """
        thread_name = threading.current_thread().name
        command_output = self._execute_command("sdkmanager --list")
        if not command_output:
            logging.error(f"[{thread_name}] Не удалось получить список пакетов.")
            return []

        installed_packages = []
        is_installed_section = False

        for line in command_output.splitlines():
            line = line.strip()

            # Начало раздела "Installed packages"
            if "Installed packages:" in line:
                is_installed_section = True
                continue

            # Останавливаем парсинг на следующем заголовке (Available Packages или Updates)
            if "Available Packages:" in line or "Available Updates:" in line:
                break

            # Если находимся в разделе "Installed packages", собираем строки с пакетами
            if is_installed_section and line.strip():
                # Берём первую колонку (пакет) из строки
                package_name = line.split()[0]
                installed_packages.append(package_name)

        return installed_packages


    def _download_system_image(self, system_image):
        """
        Скачивает указанный системный образ, если он отсутствует.
        """
        thread_name = threading.current_thread().name
        logging.info(f"[{thread_name}] Проверка наличия системного образа {system_image}...")
        list_installed_images = self._get_installed_packages()
        if system_image not in (list_installed_images or ""):
            logging.info(f"[{thread_name}] Образ {system_image} отсутствует. Начинаю загрузку...")

            # Запускаем команду скачивания в фоне, чтобы можно было отслеживать прогресс
            download_command = f"sdkmanager \"{system_image}\" --verbose"

            result = self._execute_command(download_command)

            if result is not None:
                logging.info(f"[{thread_name}] Образ {system_image} успешно загружен.")
            else:
                logging.error(f"[{thread_name}] Не удалось загрузить системный образ {system_image}.")


    def start_emulator_with_snapshot(self, avd_name, port, snapshot_name="default"):
        command = f"emulator -avd {avd_name} -port {port} -snapshot {snapshot_name} -no-snapshot-save"
        process = subprocess.Popen(command, shell=True)
        logging.info(f"[{avd_name}] Эмулятор запущен с использованием снепшота '{snapshot_name}'.")
        return process


    def start_emulator(self, avd_name, port):
        """
        Запускает эмулятор на указанном ADB-порту.
        """
        thread_name = threading.current_thread().name
        logging.info(f"[{thread_name}] Запускаем эмулятор {avd_name}...")
        command = f"emulator -avd {avd_name} -port {port} -snapshot-save-on-exit"
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        if process:
            logging.info(f"[{thread_name}] Эмулятор {avd_name} успешно запущен на указанном ADB-порту {port}.")
            return process
        else:
            raise RuntimeError(f"[{thread_name}] Не удалось запустить эмулятор {avd_name} на порту {port}.")


    def wait_for_emulator_ready(self, port, avd_ready_timeout=600):
        """
        Ожидает готовности эмулятора.
        """
        thread_name = threading.current_thread().name
        logging.info(f"[{thread_name}] Ожидание готовности эмулятора...")

        start_time = time.time()
        while time.time() - start_time < avd_ready_timeout:
            boot_status = self._execute_command(f"adb -s emulator-{port} shell getprop sys.boot_completed")
            if boot_status == "1":
                logging.info(f"[{thread_name}] Эмулятор готов к работе.")
                return True
            else:
                logging.error(f"[{thread_name}] Эмулятор пока еще не готов к работе. Ожидаем...")
            time.sleep(20)
        logging.error(f"[{thread_name}] Эмулятор не стал готов к работе в отведённое время.")
        return False


    def start_or_create_emulator(
            self,
            avd_name:str,
            port: int,
            system_image: str,
            ram_size: str,
            disk_size: str,
            avd_ready_timeout: int):
        """
        Создаёт или запускает эмулятор, ожидая его готовности.
        """
        thread_name = threading.current_thread().name

        try:
            # Проверяем, существует ли эмулятор, и создаём его при отсутствии.
            if not self._check_if_emulator_exists(avd_name):
                logging.info(f"[{thread_name}] Эмулятор {avd_name} отсутствует. Создаю новый эмулятор...")
                if self._create_emulator(avd_name, system_image):
                    self._update_avd_config(avd_name, ram_size=f"{ram_size}", disk_size=f"{disk_size}")
                    logging.info(f"[{thread_name}] Эмулятор {avd_name} успешно создан.")
            else:
                logging.error(f"[{thread_name}] Не удалось создать эмулятор {avd_name}. Прерывание...")
                return False

            # Запускаем эмулятор.
            self.start_emulator(avd_name, port)

            # Ожидаем готовности.
            if not self.wait_for_emulator_ready(port=port, avd_ready_timeout=avd_ready_timeout):
                logging.error(f"[{thread_name}] Эмулятор {avd_name} не готов к работе.")
                return False
            return True

        except Exception as e:
            logging.error(f"[{thread_name}] Ошибка при создании или запуске эмулятора {avd_name}: {e}")
            return False


    @staticmethod
    def setup_driver(avd_name, platform_version, emulator_port, android_driver_manager):
        """
        Настраивает драйвер Appium для взаимодействия с эмулятором.
        """
        android_driver_manager.start_appium_server()
        # android_driver_manager.ensure_adb_connection()
        driver = android_driver_manager.create_driver(
            avd_name=avd_name,
            emulator_port=emulator_port,
            platform_version=platform_version
        )
        return driver


    def _update_avd_config(self, avd_name, ram_size="2048", disk_size="8192M"):
        """
        Обновляет параметры AVD после его создания: RAM, Disk Size, GPU.
        """
        thread_name = threading.current_thread().name

        logging.info(f"[{thread_name}] Обновление конфигурации AVD {avd_name}...")
        config_path = os.path.expanduser(f"~/.android/avd/{avd_name}.avd/config.ini")
        if os.path.exists(config_path):
            updated_lines = []
            try:
                with open(config_path, "r") as file:
                    for line in file:
                        if line.startswith("hw.ramSize"):
                            line = f"hw.ramSize={ram_size}\n"
                        elif line.startswith("disk.dataPartition.size"):
                            line = f"disk.dataPartition.size={disk_size}\n"
                        elif line.startswith("hw.gpu.enabled"):
                            line = "hw.gpu.enabled=yes\n"
                        elif line.startswith("hw.gpu.mode"):
                            line = "hw.gpu.mode=auto\n"
                        updated_lines.append(line)
            except Exception as e:
                logging.error(f"[{thread_name}] Ошибка в обновлении конфига AVD: {e}")

            # Добавляем параметры, если они отсутствуют
            if not any("hw.ramSize" in l for l in updated_lines):
                updated_lines.append(f"hw.ramSize={ram_size}\n")
            if not any("disk.dataPartition.size" in l for l in updated_lines):
                updated_lines.append(f"disk.dataPartition.size={disk_size}\n")
            if not any("hw.gpu.enabled" in l for l in updated_lines):
                updated_lines.append("hw.gpu.enabled=yes\n")
            if not any("hw.gpu.mode" in l for l in updated_lines):
                updated_lines.append("hw.gpu.mode=auto\n")

            # Записываем обновлённый конфиг
            with open(config_path, "w") as file:
                file.writelines(updated_lines)
            logging.info(f"[{thread_name}] Конфигурация AVD {avd_name} успешно обновлена.")
        else:
            logging.error(f"[{thread_name}] Конфигурационный файл {config_path} не найден.")


    def delete_emulator(self, avd_name, port, snapshot_name):
        """
        Удаляет эмулятор с указанным именем.
        """
        thread_name = threading.current_thread().name

        try:
            logging.info(f"[{thread_name}] Удаление эмулятора {avd_name}...")
            delete_command = f"avdmanager delete avd -n {avd_name}"
            result = self._execute_command(delete_command)
            if result is not None:
                logging.info(f"[{thread_name}] Эмулятор {avd_name} успешно удалён.")
                self.delete_snapshot(avd_name, port, snapshot_name)
                return True
            else:
                logging.error(f"[{thread_name}] Не удалось удалить эмулятор {avd_name}.")
                return False
        except Exception as e:
            logging.error(f"[{thread_name}] Ошибка при удалении эмулятора {avd_name}: {e}")
            return False


    def save_snapshot(self, avd_name, port, snapshot_name):
        command = f"adb -s emulator-{port} emu avd snapshot save {snapshot_name}"
        result = subprocess.run(command, shell=True, capture_output=True)
        if result.returncode == 0:
            logging.info(f"[{avd_name}] Снепшот '{snapshot_name}' успешно сохранён.")
        else:
            logging.error(f"[{avd_name}] Ошибка сохранения снепшота: {result.stderr.decode()}")


    def delete_snapshot(self, avd_name, port, snapshot_name):
        command = f"adb -s emulator-{port} emu avd snapshot delete {snapshot_name}"
        result = subprocess.run(command, shell=True, capture_output=True)
        if result.returncode == 0:
            logging.info(f"[{avd_name}] Снепшот '{snapshot_name}' успешно удалён.")
        else:
            logging.error(f"[{avd_name}] Ошибка удаления снепшота: {result.stderr.decode()}")