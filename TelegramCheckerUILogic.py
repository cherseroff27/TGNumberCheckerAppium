import glob
import json
import os
import sys

import pandas as pd

from EmulatorAuthConfigManager import EmulatorAuthConfigManager
from EmulatorManager import EmulatorManager
from AndroidToolManager import AndroidToolManager

from logger_config import Logger
logger = Logger.get_logger(__name__)

if hasattr(sys, 'frozen'):  # Программа запущена как .exe файл
    BASE_PROJECT_DIR = os.path.abspath(os.path.dirname(sys.executable))
else:  # Программа запущена как скрипт .py
    BASE_PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))


class TelegramCheckerUILogic:
    THREADS_AMOUNT_CONFIG_FILE = "threads_config.json"  # Имя файла для хранения параметров

    def __init__(
            self,
            config_file,
            default_excel_dir: str,
            emulator_auth_config_manager: EmulatorAuthConfigManager,
            emulator_manager: EmulatorManager,
    ):
        self.config_file = config_file

        self.emulator_manager = emulator_manager
        self.android_tool_manager = AndroidToolManager(tools_installation_dir=BASE_PROJECT_DIR)

        self.default_excel_dir = default_excel_dir
        self.emulator_auth_config_manager = emulator_auth_config_manager

        # Список имен AVD, который будет заполняться через интерфейс
        self.avd_names = []


    def setup_java_and_sdk(self):
        self.android_tool_manager.setup_java_and_sdk()


    def setup_sdk_packages(self):
        self.android_tool_manager.setup_sdk_packages()


    def setup_build_tools_and_emulator(self):
        self.android_tool_manager.setup_build_tools_and_emulator()


    def remove_variables_and_paths(self):
        self.android_tool_manager.remove_paths_from_system()


    def verify_environment_setup(self):
        return self.android_tool_manager.verify_environment_setup()


    def clear_tools_files_cache(self):
        self.android_tool_manager.clear_tools_files_cache()


    def load_config_file_content(self):
        """Загружает содержимое конфигурационного файла для визуализации."""
        if not os.path.exists(self.config_file):
            logger.warning(f"Конфигурационный файл {self.config_file} не найден.")
            return {}

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при чтении конфигурационного файла: {e}")
            return {}


    def get_latest_excel_file(self):
        """Возвращает путь к последнему изменённому Excel-файлу."""
        if not os.path.exists(self.default_excel_dir):
            return ""
        files = glob.glob(os.path.join(self.default_excel_dir, "*.xlsx"))

        # Фильтруем файлы, исключая те, что содержат '_export' в имени
        filtered_files = [file for file in files if "_export" not in os.path.basename(file)]

        return max(filtered_files, key=os.path.getmtime) if files else ""


    @staticmethod
    def get_export_table_path(excel_file_path):
        """Возвращает путь для экспортируемой таблицы на основе исходного файла."""
        if not excel_file_path:
            return ""
        base, ext = os.path.splitext(excel_file_path)
        return f"{base}_export{ext}"


    @staticmethod
    def load_excel_data(file_path):
        """
        Загружает данные Excel в DataFrame. Если не удается загрузить файл, возвращает None.
        """
        if not file_path or not file_path.endswith(".xlsx"):
            raise ValueError("Некорректный файл Excel.")
        try:
            df = pd.read_excel(file_path)
            return df
        except Exception as e:
            raise ValueError(f"Ошибка загрузки Excel: {e}")

    @staticmethod
    def get_column_widths(df):
        """
        Возвращает ширину колонок на основе данных DataFrame.
        Учитывает как заголовки, так и данные в столбцах.
        """
        column_widths = {}
        for col in df.columns:
            # Преобразуем все значения столбца в строки и добавляем заголовок
            values = df[col].dropna().astype(str).tolist() + [str(col)]
            # Рассчитываем максимальную длину
            max_width = max(len(value) for value in values)
            column_widths[col] = max_width
        return column_widths

    # noinspection PyTypeChecker
    def save_threads_config(self, num_threads):
        """Сохраняет текущие параметры в файл."""
        config = {"num_threads": num_threads}
        try:
            with open(self.THREADS_AMOUNT_CONFIG_FILE, "w", encoding='utf-8') as config_file:
                json.dump(config, config_file)
                logger.info(f"В конфиг {self.THREADS_AMOUNT_CONFIG_FILE} записано дефолтное кол-во потоков {num_threads}.")
        except IOError as e:
            logger.error(f"Ошибка при сохранении параметров в {self.THREADS_AMOUNT_CONFIG_FILE}: {e}")


    def load_threads_config(self):
        """Загружает параметры из файла."""
        if os.path.exists(self.THREADS_AMOUNT_CONFIG_FILE):
            try:
                with open(self.THREADS_AMOUNT_CONFIG_FILE, "r") as config_file:
                    content = config_file.read().strip()
                    if not content:  # Если файл пуст
                        logger.warning(f"Файл {self.THREADS_AMOUNT_CONFIG_FILE} пуст. Устанавливаются значения по умолчанию.")
                        return {"num_threads": 1}
                    logger.info(f"Из конфига {self.THREADS_AMOUNT_CONFIG_FILE} извлечено дефолтное кол-во потоков: {json.loads(content).get("num_threads", 1)}.")
                    return json.loads(content)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Ошибка при чтении JSON из {self.THREADS_AMOUNT_CONFIG_FILE}: {e}")
                return {"num_threads": 1}  # Возвращаем значение по умолчанию
        else:
            logger.warning(f"Файл {self.THREADS_AMOUNT_CONFIG_FILE} не найден. Устанавливаются значения по умолчанию.")
            return {"num_threads": 1}


    def delete_all_avds(self):
        """
        Удаляет все директории AVD, указанные в конфигурации.
        """
        if self.emulator_manager.delete_all_emulators():
            logger.info("Все AVD успешно удалены.")