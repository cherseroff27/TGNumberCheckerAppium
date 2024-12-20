import os
import re
import pandas as pd
import logging

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


class ExcelDataBuilder:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path

        # Чтение исходного файла Excel
        self.df = pd.read_excel(self.input_path, header=0)  # Заголовки на первой строке
        self.df.columns = self.df.columns.str.strip()
        print(f"Заголовки таблицы: {self.df.columns.tolist()}")

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

    def get_next_row(self):
        """Получает следующую строку из таблицы и форматирует номер."""
        if not self.df.empty:
            row = self.df.iloc[0]
            formatted_number = self.format_phone_number(row['Телефон Ответчика'])
            self.df = self.df.iloc[1:]  # Удаляем обработанную строку
            if formatted_number:
                logging.info(f"Обрабатываем строку: {row.to_dict() if row is not None else 'None'}")
                row['Телефон Ответчика'] = formatted_number
                return row
        return None

    def export_registered_row(self, row):
        """Добавляет строку с подтвержденным номером в экспортную таблицу."""
        if not os.path.exists(self.output_path):
            self._create_empty_excel()

        # Проверяем, что строка имеет вид Series
        if isinstance(row, pd.Series):
            row_df = pd.DataFrame([row])  # Преобразуем в DataFrame
        else:
            row_df = row  # Если это уже DataFrame

        existing_data = pd.read_excel(self.output_path, header=0)
        updated_data = pd.concat([existing_data, row_df], ignore_index=True)
        updated_data.to_excel(self.output_path, index=False)
        logging.info(f"Строка успешно добавлена: {row_df.to_dict(orient='records')}")

    @staticmethod
    def format_phone_number(number):
        """Приводит номер телефона к формату +7xxxxxxxxxx."""
        digits = re.sub(r'\D', '', number)  # Убираем все нецифровые символы
        if len(digits) == 11 and digits.startswith('7'):
            return f'+{digits}'  # Форматируем номер в нужный вид
        return None  # Если формат не подходит, возвращаем None