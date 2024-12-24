import os
import subprocess
import sys
import threading
import time

from logger_config import Logger
logger = Logger.get_logger(__name__)


class EmulatorManager:
    def __init__(self):
        self.lock = threading.Lock()


    @staticmethod
    def _execute_command(command):
        """
        Выполняет системную команду с обработкой ошибок.
        """
        thread_name = threading.current_thread().name

        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"[{thread_name}] Command failed: {command}\nError: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"[{thread_name}] Failed to execute command: {command}\nException: {e}")
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
                logger.info(f"[{thread_name}] Эмулятор {avd_name} существует.")
                return True
            else:
                logger.info(f"[{thread_name}] Эмулятор {avd_name} отсутствует в списке AVD.")
                return False
        else:
            logger.error(f"[{thread_name}] Не удалось получить список AVD. Команда вернула пустой результат.")
            return False


    def _create_emulator(self, avd_name, system_image):
        """
        Создаёт новый эмулятор и с указанным образом.
        """
        thread_name = threading.current_thread().name
        logger.info(f"[{thread_name}] Создание эмулятора {avd_name} с образом {system_image}...")
        create_command = (
            f"avdmanager create avd -n {avd_name} -k \"{system_image}\" --device \"pixel\" --force"
        )

        result = self._execute_command(create_command)

        if result is not None:
            logger.info(f"[{thread_name}] Эмулятор {avd_name} успешно создан.")
            return True
        else:
            logger.error(f"[{thread_name}] Не удалось создать эмулятор {avd_name}.")
            return False


    def _get_installed_packages(self):
        """
        Возвращает список доступных пакетов из вывода команды 'sdkmanager --list'.
        """
        thread_name = threading.current_thread().name
        command_output = self._execute_command("sdkmanager --list")
        if not command_output:
            logger.error(f"[{thread_name}] Не удалось получить список пакетов.")
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


    def download_system_image(self, system_image):
        """
        Скачивает указанный системный образ, если он отсутствует.
        """
        thread_name = threading.current_thread().name
        logger.info(f"[{thread_name}] Проверка наличия системного образа {system_image}...")
        list_installed_images = self._get_installed_packages()
        if system_image not in (list_installed_images or ""):
            logger.info(f"[{thread_name}] Образ {system_image} отсутствует. Начинаю загрузку...")

            # Запускаем команду скачивания в фоне, чтобы можно было отслеживать прогресс
            download_command = f"sdkmanager \"{system_image}\" --verbose"

            result = self._execute_command(download_command)

            if result is not None:
                logger.info(f"[{thread_name}] Образ {system_image} успешно загружен.")
            else:
                logger.error(f"[{thread_name}] Не удалось загрузить системный образ {system_image}.")


    def wait_for_emulator_ready(self, avd_name, emulator_port, avd_ready_timeout=600):
        """
        Ожидает готовности эмулятора.
        """
        thread_name = threading.current_thread().name
        logger.info(f"[{thread_name}] Ожидание готовности эмулятора...")

        start_time = time.time()
        while time.time() - start_time < avd_ready_timeout:
            self._execute_command(f"adb -s emulator-{emulator_port} wait-for-device")
            boot_status = self._execute_command(f"adb -s emulator-{emulator_port} shell getprop sys.boot_completed")
            elapsed_time = int(time.time() - start_time)  # Время, прошедшее с начала ожидания
            if boot_status == "1":
                logger.info(f"[{thread_name}] Эмулятор готов к работе.")
                return True
            else:
                # Перезаписываем сообщение с добавлением времени ожидания
                sys.stdout.write(
                    f"\r[{thread_name}] [{avd_name}] Эмулятор пока еще не готов к работе. Ожидаем... "
                    f"Прошло: {elapsed_time} секунд."
                )
                sys.stdout.flush()
            time.sleep(1)

        # Очистка последней строки и вывод ошибки
        sys.stdout.write("\r")
        sys.stdout.flush()
        logger.error(f"[{thread_name}] [{avd_name}] Эмулятор не стал готов к работе "
                      f"за отведённое время: {avd_ready_timeout} секунд.")
        return False


    @staticmethod
    def setup_driver(avd_name, platform_version, emulator_port, android_driver_manager):
        """
        Настраивает драйвер Appium для взаимодействия с эмулятором.
        """
        android_driver_manager.start_appium_server()
        android_driver_manager.ensure_adb_connection()
        driver = android_driver_manager.create_driver(
            avd_name=avd_name,
            emulator_port=emulator_port,
            platform_version=platform_version
        )
        return driver


    def start_or_create_emulator(
            self,
            avd_name:str,
            emulator_port: int,
            system_image: str,
            ram_size: str,
            disk_size: str,
            avd_ready_timeout: int,
    ):
        """
        Создаёт или запускает эмулятор, ожидая его готовности.
        """
        thread_name = threading.current_thread().name

        try:
            # Проверяем, существует ли эмулятор, и создаём его при отсутствии.
            if not self._check_if_emulator_exists(avd_name):
                logger.info(f"[{thread_name}] Поскольку эмулятор {avd_name} отсутствует в списке AVD - создаю новый эмулятор...")
                if self._create_emulator(avd_name, system_image):
                    self._update_avd_config(avd_name, ram_size=f"{ram_size}", disk_size=f"{disk_size}")
                    logger.info(f"[{thread_name}] Эмулятор {avd_name} успешно создан.")
            else:
                logger.error(f"[{thread_name}] Не удалось создать эмулятор {avd_name}. Прерывание...")
                return False

            # Запускаем эмулятор.
            self.start_emulator_with_optional_snapshot(
                avd_name=avd_name,
                emulator_port=emulator_port,
                avd_ready_timeout=avd_ready_timeout
            )

            return True

        except Exception as e:
            logger.error(f"[{thread_name}] Ошибка при создании или запуске эмулятора {avd_name}: {e}")
            return False


    def start_emulator_with_optional_snapshot(self, avd_name, avd_ready_timeout, emulator_port):
        """
        Универсальный метод для запуска эмулятора с возможностью загрузки/создания снепшота.
        """
        thread_name = threading.current_thread().name
        snapshots_dir = os.path.expanduser(f"~/.android/avd/{avd_name}.avd/snapshots/")

        # Определение самого актуального снепшота
        latest_snapshot = None
        if os.path.exists(snapshots_dir):
            snapshots = [f for f in os.listdir(snapshots_dir) if os.path.isdir(os.path.join(snapshots_dir, f))]
            if snapshots:
                latest_snapshot = max(snapshots, key=lambda snap: os.path.getmtime(os.path.join(snapshots_dir, snap)))
                logger.info(f"[{thread_name}] Найден самый актуальный снепшот: {latest_snapshot}.")

        # Формирование команды для запуска эмулятора
        snapshot_command = f"emulator -avd {avd_name} -port {emulator_port} -gpu auto"
        if latest_snapshot:
            snapshot_command += f" -snapshot {latest_snapshot}"
            logger.info(f"[{thread_name}] Используем снепшот '{latest_snapshot}' для запуска эмулятора.")
        else:
            logger.info(f"[{thread_name}] Снепшоты отсутствуют. Эмулятор будет запущен без снепшота.")

        # Запуск эмулятора
        process = subprocess.Popen(snapshot_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        logger.info(f"[{thread_name}] Эмулятор {avd_name} запущен. Ожидание загрузки...")

        if not self.wait_for_emulator_ready(
                avd_name=avd_name,
                emulator_port=emulator_port,
                avd_ready_timeout=avd_ready_timeout
        ):
            logger.error(f"[{thread_name}] Эмулятор {avd_name} не стал готов к работе.")
            process.terminate()
            return False

        return process


    @staticmethod
    def save_snapshot(avd_name, emulator_port, snapshot_name):
        """
        Сохраняет снепшот эмулятора.
        """
        thread_name = threading.current_thread().name

        command = f"adb -s emulator-{emulator_port} emu avd snapshot save {snapshot_name}"
        result = subprocess.run(command, shell=True, capture_output=True)
        if result.returncode == 0:
            logger.info(f"[{thread_name}] [{avd_name}] Snapshot '{snapshot_name}' успешно сохранён.")
        else:
            logger.error(f"[{thread_name}] [{avd_name}] Ошибка сохранения snapshot '{snapshot_name}': {result.stderr.decode()}")


    @staticmethod
    def delete_snapshot(avd_name, emulator_port, snapshot_name):
        thread_name = threading.current_thread().name

        command = f"adb -s emulator-{emulator_port} emu avd snapshot delete {snapshot_name}"
        result = subprocess.run(command, shell=True, capture_output=True)
        if result.returncode == 0:
            logger.info(f"[{thread_name}] [{avd_name}]: Snapshot '{snapshot_name}' успешно удалён.")
        else:
            logger.error(f"[{thread_name}] [{avd_name}]: Ошибка удаления snapshot '{snapshot_name}': {result.stderr.decode()}")


    @staticmethod
    def _update_avd_config(avd_name, ram_size="1024", disk_size="2048M"):
        """
        Обновляет параметры AVD после его создания: RAM, Disk Size, GPU.
        """
        thread_name = threading.current_thread().name

        logger.info(f"[{thread_name}] Обновление конфигурации AVD {avd_name}...")
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
                logger.error(f"[{thread_name}] Ошибка в обновлении конфига AVD: {e}")

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
            logger.info(f"[{thread_name}] Конфигурация AVD {avd_name} успешно обновлена.")
        else:
            logger.error(f"[{thread_name}] Конфигурационный файл {config_path} не найден.")


    def delete_emulator(self, avd_name, emulator_port, snapshot_name):
        """
        Удаляет эмулятор с указанным именем.
        """
        thread_name = threading.current_thread().name

        try:
            logger.info(f"[{thread_name}] Удаление эмулятора {avd_name}...")
            delete_command = f"avdmanager delete avd -n {avd_name}"
            result = self._execute_command(delete_command)
            if result is not None:
                logger.info(f"[{thread_name}] Эмулятор {avd_name} успешно удалён.")
                try:
                    self.delete_snapshot(avd_name, emulator_port, snapshot_name)
                except Exception as e:
                    logger.error(f"[{thread_name}] Ошибка при удалении snapshot {avd_name}: {e}")
                    return True
                return True
            else:
                logger.error(f"[{thread_name}] Не удалось удалить эмулятор {avd_name}.")
                return False
        except Exception as e:
            logger.error(f"[{thread_name}] Ошибка при удалении эмулятора {avd_name}: {e}")
            return False


    def close_emulator(self, thread_name, avd_name, emulator_port):
        try:
            stop_command = f"adb -s emulator-{emulator_port} emu kill"
            result = self._execute_command(stop_command)
            if result is not None:
                logger.info(f"[{thread_name}] Эмулятор {avd_name} на порту {emulator_port} успешно завершён.")
                return True
            else:
                logger.error(f"[{thread_name}] Не удалось завершить эмулятор {avd_name} на порту {emulator_port}.")
                return False
        except Exception as e:
            logger.error(f"[{thread_name}] Ошибка при завершении работы эмулятора {avd_name} на порту {emulator_port}: {e}")
            return False


    def delete_all_emulators(self):
        """
        Удаляет все установленные AVD на устройстве.
        """
        thread_name = threading.current_thread().name

        try:
            # Получаем список всех AVD
            command = "emulator -list-avds"
            avd_list = self._execute_command(command)

            if not avd_list:
                logger.info(f"[{thread_name}] Список AVD пуст. Удаление не требуется.")
                return True

            avds = avd_list.splitlines()
            logger.info(f"[{thread_name}] Найдено {len(avds)} AVD: {', '.join(avds)}.")

            for avd_name in avds:
                logger.info(f"[{thread_name}] Удаление AVD {avd_name}...")
                delete_command = f"avdmanager delete avd -n {avd_name}"
                result = self._execute_command(delete_command)
                if result:
                    logger.info(f"[{thread_name}] AVD {avd_name} успешно удалён.")
                else:
                    logger.error(f"[{thread_name}] Не удалось удалить AVD {avd_name}. Продолжаем удаление остальных.")
            return True
        except Exception as e:
            logger.error(f"[{thread_name}] Ошибка при удалении всех AVD: {e}")
            return False


    @staticmethod
    def get_avd_list():
        """
        Возвращает список доступных AVD, используя emulator -list-avds.
        """
        try:
            # Выполнение команды emulator -list-avds
            result = subprocess.run(
                ["emulator", "-list-avds"],
                capture_output=True,
                text=True,
                check=True
            )
            avd_list = result.stdout.splitlines()
            return avd_list
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при вызове emulator: {e}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при обработке списка AVD: {e}")
            return []