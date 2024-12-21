import glob
import json
import os

from EmulatorAuthConfigManager import EmulatorAuthConfigManager
import pandas as pd

import logging

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


class TelegramCheckerUILogic:
    def __init__(self, config_file, default_excel_dir: str, emulator_auth_config_manager: EmulatorAuthConfigManager):
        self.config_file = config_file
        self.default_excel_dir = default_excel_dir
        self.emulator_auth_config_manager = emulator_auth_config_manager

        # Список имен AVD, который будет заполняться через интерфейс
        self.avd_names = []

    def load_config_file_content(self):
        """Загружает содержимое конфигурационного файла для визуализации."""
        if not os.path.exists(self.config_file):
            logging.warning(f"Конфигурационный файл {self.config_file} не найден.")
            return {}

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка при чтении конфигурационного файла: {e}")
            return {}

    def get_latest_excel_file(self):
        """Возвращает путь к последнему изменённому Excel-файлу."""
        if not os.path.exists(self.default_excel_dir):
            return ""
        files = glob.glob(os.path.join(self.default_excel_dir, "*.xlsx"))

        # Фильтруем файлы, исключая те, что содержат '_export' в имени
        filtered_files = [file for file in files if "_export" not in os.path.basename(file)]

        return max(filtered_files, key=os.path.getmtime) if files else ""

    def get_export_table_path(self, excel_file_path):
        """Возвращает путь для экспортируемой таблицы на основе исходного файла."""
        if not excel_file_path:
            return ""
        base, ext = os.path.splitext(excel_file_path)
        return f"{base}_export{ext}"

    def load_excel_data(self, file_path):
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

    def get_column_widths(self, df):
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