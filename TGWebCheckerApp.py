import os
import threading
import tkinter as tk

import pandas as pd
from colorama import Fore, Style, init
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from ExcelDataBuilder import ExcelDataBuilder
from ProfileConfigHandler import ProfileConfigHandler
from TGWebAutomation import TelegramWebAutomation
from TelegramCheckerUILogic import TelegramCheckerUILogic
from TelegramCheckerUI import TelegramCheckerUI

# Логирование
import logging


# Инициализация colorama
init(autoreset=True)

# Путь по умолчанию
DEFAULT_BROWSER_PROFILES_DIR = os.path.abspath("browser_profiles_dir")
DEFAULT_EXCEL_TABLE_DIR = os.path.abspath("excel_tables_dir")
reg_numbers_counter = 0
unreg_numbers_counter = 0

logging.basicConfig(
    format=f"%(asctime)s {Fore.CYAN}%(threadName)s{Style.RESET_ALL} - %(levelname)s: %(message)s",
    level=logging.DEBUG,  # По умолчанию показываем все уровни
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Добавление цветов для уровней логирования
LOG_COLORS = {
    "DEBUG": Fore.LIGHTBLUE_EX,
    "INFO": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.MAGENTA,
}


class ColorFormatter(logging.Formatter):
    def format(self, record):
        log_color = LOG_COLORS.get(record.levelname, "")
        record.msg = f"{log_color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


for handler in logging.root.handlers:
    handler.setFormatter(ColorFormatter(handler.formatter._fmt))


class ThreadSafeExcelProcessor:
    def __init__(self, input_path, output_path):
        self.excel_data_builder = ExcelDataBuilder(input_path, output_path)
        self.lock = Lock()  # Для синхронизации доступа к данным
        self.processed_numbers = self.load_processed_numbers()  # Загружаем уже обработанные номера
        logging.info(f"Загружено {len(self.processed_numbers)} обработанных номеров из экспортной таблицы.")
        self.is_numbers_ended = False


    def normalize_phone_number(self, phone):
        """Нормализует формат номера телефона."""
        phone = str(phone).strip()
        if phone.startswith("'"):
            phone = phone[1:]  # Убираем апостроф
        return phone if phone.startswith('+') else f"+{phone.lstrip('0')}"


    def load_processed_numbers(self):
        """Загружает номера из экспортной таблицы с нормализацией."""
        if os.path.exists(self.excel_data_builder.output_path):
            try:
                logging.debug(f"Загружаем данные из экспортной таблицы: {self.excel_data_builder.output_path}")
                processed_data = pd.read_excel(self.excel_data_builder.output_path, dtype=str, engine='openpyxl')
                processed_numbers = {self.normalize_phone_number(num) for num in processed_data['Телефон Ответчика']}
                logging.info(f"Загружено {len(processed_numbers)} обработанных номеров.")
                return processed_numbers
            except Exception as e:
                logging.error(f"Ошибка при загрузке экспортной таблицы: {e}")
                return set()
        logging.warning("Экспортная таблица не найдена.")
        return set()


    def filter_unprocessed_numbers(self):
        """Исключает уже обработанные номера из исходной таблицы."""
        initial_count = len(self.excel_data_builder.df)
        logging.info(f"Изначально номеров для обработки: {initial_count}")

        self.excel_data_builder.df['Телефон Ответчика'] = self.excel_data_builder.df['Телефон Ответчика'].astype(str)
        self.excel_data_builder.df['Телефон Ответчика'] = self.excel_data_builder.df['Телефон Ответчика'].apply(
            self.normalize_phone_number
        )
        self.excel_data_builder.df = self.excel_data_builder.df[
            ~self.excel_data_builder.df['Телефон Ответчика'].isin(self.processed_numbers)
        ]
        filtered_count = len(self.excel_data_builder.df)
        logging.info(f"Фильтрация завершена. Осталось для обработки: {filtered_count} из {initial_count}.")



    def get_next_number(self):
        with self.lock:
            if not self.excel_data_builder.df.empty:
                row = self.excel_data_builder.df.iloc[0]
                logging.debug(f"Выдан номер для обработки: {row['Телефон Ответчика']}.")
                self.excel_data_builder.df = self.excel_data_builder.df.iloc[1:]  # Удаляем строку из DataFrame
                return row
            else:
                logging.info("DataFrame пуст, все номера обработаны.")
                self.is_numbers_ended = True
                return None

    def record_valid_number(self, row):
        global reg_numbers_counter
        global unreg_numbers_counter

        thread_name = threading.current_thread().name
        normalized_row_number = self.normalize_phone_number(row['Телефон Ответчика'])

        with self.lock:
            if os.path.exists(self.excel_data_builder.output_path):
                current_data = pd.read_excel(self.excel_data_builder.output_path, dtype=str, engine='openpyxl')
            else:
                current_data = pd.DataFrame(columns=self.excel_data_builder.df.columns)

            if normalized_row_number in current_data['Телефон Ответчика'].str.strip().apply(self.normalize_phone_number).values:
                logging.info(f"[{thread_name}] Номер {normalized_row_number} уже существует, пропускаем.")
                unreg_numbers_counter = unreg_numbers_counter + 1
                return

            row['Телефон Ответчика'] = normalized_row_number
            updated_data = pd.concat([current_data, pd.DataFrame([row])], ignore_index=True)
            updated_data.to_excel(self.excel_data_builder.output_path, index=False, engine='openpyxl')

            self.processed_numbers.add(normalized_row_number)
            logging.info(f"[{thread_name}] Номер {normalized_row_number} добавлен в экспортную таблицу.")
            reg_numbers_counter = reg_numbers_counter + 1


class TelegramCheckerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.profile_manager = ProfileConfigHandler()
        self.logic = TelegramCheckerUILogic(
            browser_profiles_dir=DEFAULT_BROWSER_PROFILES_DIR,
            default_excel_dir=DEFAULT_EXCEL_TABLE_DIR,
            profile_manager=self.profile_manager
        )
        self.ui = TelegramCheckerUI(self.root, self.logic, self)
        self.ui.refresh_excel_table()
        self.profile_queue = None
        self.should_finish_work = False


    def run_multithreaded_automation(self):
        profiles = [f for f in os.listdir(self.ui.browser_profiles_dir.get()) if
                    os.path.isdir(os.path.join(self.ui.browser_profiles_dir.get(), f))]

        logging.info(f"Имена всех профилей: {profiles}")
        source_xlsx = app.ui.source_excel_file_path.get()
        logging.info(f"Исходный файл таблицы: {source_xlsx}")
        xlsx_for_export = app.ui.export_table_path.get()
        logging.info(f"Экспортный файл таблицы: {xlsx_for_export}")

        excel_data_builder = ThreadSafeExcelProcessor(source_xlsx, xlsx_for_export)

        max_workers = min(self.ui.num_threads.get(), len(profiles))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for profile_name in profiles:
                logging.info(f"Назначен профиль: {profile_name}")

                executor.submit(
                    self.process_profile,
                    profile_name=profile_name,
                    excel_data_builder=excel_data_builder,
                    profile_manager=app.profile_manager
                )

    def process_profile(self, profile_name, excel_data_builder, profile_manager):
        while not excel_data_builder.is_numbers_ended:
            thread_name = threading.current_thread().name
            logging.debug(f"[{thread_name}] Обрабатывается профиль: {profile_name}")

            telegram_web_automation = TelegramWebAutomation(profile_manager, excel_data_builder,
                                                            DEFAULT_BROWSER_PROFILES_DIR)
            telegram_web_automation.setup_driver(profile_name)

            try:
                telegram_web_automation.authorize_if_needed(profile_name)
                while True:
                    row = excel_data_builder.get_next_number()
                    if row is None:
                        break

                    number = row['Телефон Ответчика']
                    logging.debug(f"[{thread_name}] Номер в исходном виде: {number}")
                    formatted_number = ExcelDataBuilder.format_phone_number(number)
                    if formatted_number:
                        logging.info(f"[{thread_name}] Пытаемся добавить в контакты номер [{number}]")
                        if telegram_web_automation.add_contact(formatted_number):
                            row['Телефон Ответчика'] = formatted_number
                            excel_data_builder.record_valid_number(row)
                    else:
                        logging.warning(f"[{thread_name}] Неверный формат номера [{number}]")

                logging.info(f"[{thread_name}] Обработка профиля {profile_name} завершена.")

            finally:
                if telegram_web_automation.driver:
                    telegram_web_automation.driver.quit()


if __name__ == "__main__":
    app = TelegramCheckerApp()
    app.root.mainloop()

    logging.info(f"Работал с таблицей {app.ui.source_excel_file_path.get()}.")
    logging.info(f"Экспортировал подтвержденные номера в таблицу {app.ui.export_table_path.get()}.")
    logging.info(f"Подтверждена регистрация {reg_numbers_counter} номеров из {reg_numbers_counter + unreg_numbers_counter}.")
    logging.info(f"Не подтверждена регистрация {unreg_numbers_counter} номеров из {reg_numbers_counter + unreg_numbers_counter}.")
