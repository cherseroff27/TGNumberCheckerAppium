import os
import re

import pandas as pd


class ExcelDataBuilder:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path

        # Чтение исходного файла Excel
        self.df = pd.read_excel(self.input_path, header=0)  # Заголовки на первой строке
        self.df.columns = self.df.columns.str.strip()
        print(f"[DEBUG] Заголовки таблицы: {self.df.columns.tolist()}")

        # Проверка наличия столбца
        if 'Телефон Ответчика' not in self.df.columns:
            raise ValueError("В таблице отсутствует столбец 'Телефон Ответчика'")

        # Создание пустого файла Excel с нужной структурой, если он не существует
        if not os.path.exists(self.output_path):
            self._create_empty_excel()
            print(f"Пустой файл Excel создан по пути: {self.output_path}")


    def _create_empty_excel(self):
        """Создает пустой Excel-файл с такой же структурой, как в self.df."""
        # Парсим директорию и имя файла из self.output_path
        directory = os.path.dirname(self.output_path)

        # Создаем директорию, если она не существует
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        # Создаем пустой DataFrame с той же структурой и сохраняем
        empty_df = self.df.iloc[0:0]  # Пустой DataFrame с колонками из исходного файла
        empty_df.to_excel(self.output_path, index=False)


    def get_phone_numbers(self):
        return self.df['Телефон Ответчика'].dropna().apply(lambda x: f"+{str(x).replace('-', '').replace(' ', '')}")


    def export_registered_contacts(self, registered_numbers):
        registered_rows = self.df[self.df['Телефон Ответчика'].isin(registered_numbers)]
        registered_rows.to_excel(self.output_path, index=False)


    @staticmethod
    def format_phone_number(number):
        # Оставляем только цифры и приводим к формату +7xxxxxxxxxx
        digits = re.sub(r'\D', '', number)  # Убираем все нецифровые символы
        if len(digits) == 11 and digits.startswith('7'):
            return f'+{digits}'  # Форматируем номер в нужный вид
        return None  # Если формат не подходит, возвращаем None
