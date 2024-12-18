import glob
import os
from fileinput import filename

import pandas as pd


class TelegramCheckerUILogic:
    def __init__(self, browser_profiles_dir: str, default_excel_dir: str, profile_manager):
        self.browser_profiles_dir = browser_profiles_dir
        self.profile_manager = profile_manager
        self.default_excel_dir = default_excel_dir

    def get_profiles_dir(self):
        """
        Возвращает путь к папке с профилями браузеров. Если папка не существует, создаёт её.
        """
        if not os.path.exists(self.browser_profiles_dir):
            os.makedirs(self.browser_profiles_dir)
        return self.browser_profiles_dir

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

    def load_profiles_to_treeview(self, treeview):
        """
        Загружает список профилей из папки и отображает в Treeview.
        """
        # Очистим текущие данные в Treeview
        treeview.delete(*treeview.get_children())

        # Получаем список файлов/папок
        profiles_path = self.browser_profiles_dir
        if not os.path.exists(profiles_path):
            return

        profiles = os.listdir(profiles_path)

        # Добавляем данные в Treeview
        for profile in profiles:
            treeview.insert("", "end", values=(profile,))
