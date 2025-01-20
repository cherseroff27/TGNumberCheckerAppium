import glob
import json
import os

import pandas as pd

from EmulatorManager import EmulatorManager
from AndroidToolManager import AndroidToolManager
from AppiumInstaller import AppiumInstaller
from NodeJsInstaller import NodeJsInstaller
from PackageManager import PackageManager

from logger_config import Logger
logger = Logger.get_logger(__name__)


class TelegramCheckerUILogic:
    DEFAULT_THREADS_AMOUNT_CONFIG = {
        "threads_amount": 1,  # Количество потоков по умолчанию
    }
    THREADS_AMOUNT_CONFIG_FILE = "threads_amount_config.json"  # Имя файла для хранения количества потоков

    DEFAULT_AVD_CONFIG = {
        "ram_size": 1024,  # Размер ОЗУ по умолчанию в МБ
        "disk_size": 1024,  # Размер постоянной памяти по умолчанию в МБ
        "emulator_ready_timeout": 1200,  # Время ожидания готовности эмулятора в секундах
    }
    AVD_PROPERTIES_CONFIG_FILE = "avd_properties_config.json"  # Имя файла для хранения параметров AVD

    def __init__(
            self,
            temp_files_dir: str,
            default_excel_dir: str,
            avd_list_info_config_file,
            emulator_manager: EmulatorManager,
            appium_installer: AppiumInstaller,
            node_js_installer: NodeJsInstaller,
            android_tool_manager: AndroidToolManager,
    ):
        self.default_excel_dir = default_excel_dir
        self.temp_files_dir = temp_files_dir

        self.avd_config = self.load_avd_properties_config()
        self.avd_list_info_config_file = avd_list_info_config_file

        self.appium_installer = appium_installer
        self.node_js_installer = node_js_installer
        self.android_tool_manager = android_tool_manager

        self.emulator_manager = emulator_manager


    def verify_environment_setup(self):
        self.node_js_installer.verify_node_js_environment_setup()
        self.android_tool_manager.verify_sdk_tools_environment_setup()


    def download_and_setup_java_sdk_and_android_sdk_tools(self):
        self.android_tool_manager.setup_all()


    def download_and_setup_node_js(self):
        self.node_js_installer.setup_all()


    def setup_appium_and_uiautomator2(self):
        self.appium_installer.setup_appium_and_uiautomator2()


    def check_if_is_node_installed(self):
        return self.node_js_installer.fetch_node_version()


    def restart_adb_server(self):
        self.android_tool_manager.restart_adb_server()


    def clear_tools_files_cache(self):
        PackageManager.clear_tools_files_cache(self.temp_files_dir)


    def load_config_file_content(self):
        """Загружает содержимое общего для всех AVD конфигурационного файла для визуализации."""
        if not os.path.exists(self.avd_list_info_config_file):
            logger.warning(f"Конфигурационный файл {self.avd_list_info_config_file} не найден.")
            return {}

        try:
            with open(self.avd_list_info_config_file, 'r', encoding='utf-8') as f:
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
        """Загружает параметры количества потоков из файла."""
        if os.path.exists(self.THREADS_AMOUNT_CONFIG_FILE):
            try:
                with open(self.THREADS_AMOUNT_CONFIG_FILE, "r") as config_file:
                    content = config_file.read().strip()
                    if not content:  # Если файл пуст
                        logger.warning(f"Файл {self.THREADS_AMOUNT_CONFIG_FILE} пуст.")
                        return {"num_threads": 1}
                    logger.info(f"Из конфига {self.THREADS_AMOUNT_CONFIG_FILE} извлечено дефолтное кол-во потоков: {json.loads(content).get("num_threads", 1)}.")
                    return json.loads(content)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Ошибка при чтении JSON из {self.THREADS_AMOUNT_CONFIG_FILE}: {e}")
        else:
            logger.warning(f"Файл {self.THREADS_AMOUNT_CONFIG_FILE} не найден.")

        logger.info(f"Используются значения по умолчанию: {self.DEFAULT_THREADS_AMOUNT_CONFIG}")
        return self.DEFAULT_THREADS_AMOUNT_CONFIG


    def load_avd_properties_config(self):
        """
        Загружает конфиг AVD. Если файл отсутствует, возвращает значения по умолчанию.
        """
        if os.path.exists(self.AVD_PROPERTIES_CONFIG_FILE):
            try:
                with open(self.AVD_PROPERTIES_CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # Логирование загруженных параметров
                    logger.info(f"Загружены параметры эмуляторов из файла {self.AVD_PROPERTIES_CONFIG_FILE}:")
                    for key, value in config.items():
                        logger.info(f"{key}: {value}")

                    return {**self.DEFAULT_AVD_CONFIG, **config}
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Ошибка при чтении конфигурационного файла {self.AVD_PROPERTIES_CONFIG_FILE}: {e}")
        else:
            logger.warning(f"Файл {self.AVD_PROPERTIES_CONFIG_FILE} не найден.")
        # Логирование использования значений по умолчанию
        logger.info(f"Используются значения по умолчанию: {self.DEFAULT_AVD_CONFIG}")
        return self.DEFAULT_AVD_CONFIG


    # noinspection PyTypeChecker
    def save_avd_properties_config(self, config):
        """
        Сохраняет конфиг AVD в файл.
        :param config: Словарь с параметрами конфигурации
        """
        try:
            with open(self.AVD_PROPERTIES_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except IOError as e:
            logger.error(f"Ошибка при сохранении конфигурационного файла: {e}")


    def get_avd_property(self, avd_property_name):
        """
        Возвращает значение конкретного параметра AVD.
        :param avd_property_name: Имя параметра
        """
        return self.avd_config.get(avd_property_name, self.DEFAULT_AVD_CONFIG.get(avd_property_name))


    def set_avd_property(self, avd_property_name, value):
        """
        Устанавливает значение параметра и сохраняет конфиг.
        :param avd_property_name: Имя параметра
        :param value: Значение параметра
        """
        self.avd_config[avd_property_name] = value
        self.save_avd_properties_config(self.avd_config)


    def delete_all_avds(self):
        """
        Удаляет все директории AVD, указанные в конфигурации.
        """
        if self.emulator_manager.delete_all_emulators():
            logger.info("Все AVD успешно удалены.")