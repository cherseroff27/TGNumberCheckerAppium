import os
import re
import requests
import subprocess
from tqdm import tqdm

from logger_config import Logger
logger = Logger.get_logger(__name__)


class TelegramApkVersionManager:
    def __init__(self, telegram_app_package):
        self.something = None
        self.telegram_app_package = telegram_app_package


    @staticmethod
    def get_app_version(apk_path):
        """Извлекает версию приложения из APK-файла с помощью aapt."""
        try:
            result = subprocess.run(
                ["aapt", "dump", "badging", apk_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            version_match = re.search(r"versionName='([\d.]+)'", result.stdout)
            if version_match:
                return version_match.group(1)
            else:
                raise ValueError("Не удалось извлечь версию из APK")
        except Exception as e:
            logger.error(f"Ошибка при извлечении версии из APK: {e}")
            return None


    def get_installed_app_version(self, emulator_port):
        """Извлекает версию установленного приложения с устройства."""
        try:
            command = ["adb", "-s", f"emulator-{emulator_port}", "shell", f"dumpsys package {self.telegram_app_package}"]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            version_match = re.search(r"versionName=([\d.]+)", result.stdout)
            if version_match:
                return version_match.group(1)
            else:
                raise ValueError("Не удалось извлечь версию установленного приложения")
        except Exception as e:
            logger.error(f"Ошибка при извлечении версии установленного приложения: {e}")
            return None


    @staticmethod
    def download_latest_telegram_apk(download_url, save_dir, apk_name):
        """
        Скачивает APK-файл Telegram с прогресс-баром и сохраняет его в указанную директорию.

        :param download_url: URL для скачивания APK
        :param save_dir: Директория для сохранения файла
        :param apk_name: Имя APK файла без расширения
        :return: Путь к скачанному файлу
        """
        # Создаем папку, если её нет
        os.makedirs(save_dir, exist_ok=True)

        # Указываем путь для сохранения файла
        apk_file_path = os.path.join(save_dir, f"{apk_name}.apk")

        try:
            logger.info("Начинается скачивание актуальной версии Telegram APK...")

            # Делаем HEAD-запрос для получения размера файла
            with requests.get(download_url, stream=True) as response:
                response.raise_for_status()  # Проверяем успешность запроса
                total_size = int(response.headers.get('content-length', 0))

                # Сохраняем файл на диск с отображением прогресса
                with open(apk_file_path, "wb") as apk_file, tqdm(
                        desc="Downloading Telegram APK",
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024
                ) as progress_bar:
                    for chunk in response.iter_content(chunk_size=8192):
                        apk_file.write(chunk)
                        progress_bar.update(len(chunk))

            logger.info(f"Скачивание завершено. Актуальная версия Telegram сохранена в: {apk_file_path}")
            return apk_file_path

        except requests.RequestException as e:
            raise RuntimeError(f"Ошибка при скачивании APK: {e}")