import os
import re

import pandas as pd

from logger_config import Logger
logger = Logger.get_logger(__name__)


class ExcelDataBuilder:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path

        # Чтение исходного файла Excel
        self.df = pd.read_excel(self.input_path, header=0, dtype=str, engine='openpyxl')
        self.df.columns = self.df.columns.str.strip()
        logger.info(f"Заголовки таблицы: {self.df.columns.tolist()}")

        if 'Телефон Ответчика' not in self.df.columns:
            raise ValueError("В таблице отсутствует столбец 'Телефон Ответчика'")

        if not os.path.exists(self.output_path):
            self._create_empty_excel()
            logger.info(f"Пустой файл Excel создан по пути: {self.output_path}")

    def _create_empty_excel(self):
        directory = os.path.dirname(self.output_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        empty_df = self.df.iloc[0:0]
        empty_df.to_excel(self.output_path, index=False, engine='openpyxl')

    @staticmethod
    def format_phone_number(number):
        digits = re.sub(r'\D', '', number)
        if len(digits) == 11 and digits.startswith('7'):
            return f'+{digits}'
        return None
