import os
import re
import threading

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pandas as pd
from appium.webdriver.extensions.android.nativekey import AndroidKey

from ExcelDataBuilder import ExcelDataBuilder
from TGMobileAppAutomation import TelegramMobileAppAutomation
from EmulatorAuthConfigManager import EmulatorAuthConfigManager
from AndroidDriverManager import AndroidDriverManager
from EmulatorManager import EmulatorManager

import logging

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


DEFAULT_EXCEL_TABLE_DIR = os.path.abspath("excel_tables_dir")


class ThreadSafeExcelProcessor:
    def __init__(self, input_path, output_path):
        self.excel_data_builder = ExcelDataBuilder(input_path, output_path)
        self.lock = Lock()
        self.processed_numbers = self.load_processed_numbers()
        logging.info(f"Загружено {len(self.processed_numbers)} обработанных номеров.")
        self.is_numbers_ended = False

    def load_processed_numbers(self):
        if os.path.exists(self.excel_data_builder.output_path):
            try:
                processed_data = pd.read_excel(self.excel_data_builder.output_path, dtype=str, engine='openpyxl')
                return {self.normalize_phone_number(num) for num in processed_data['Телефон Ответчика']}
            except Exception as e:
                logging.error(f"Ошибка при загрузке экспортной таблицы: {e}")
                return set()
        return set()

    @staticmethod
    def normalize_phone_number(phone):
        phone = str(phone).strip()
        digits = re.sub(r'\D', '', phone)  # Удалить все символы, кроме цифр
        if len(digits) == 11 and digits.startswith('7'):  # Российские номера (например, 7XXXXXXXXXX)
            return f'+{digits}'
        elif len(digits) == 10 and not digits.startswith('7'):  # Если номер содержит 10 цифр
            return f'+7{digits}'  # Преобразуем в международный формат
        logging.warning(f"Некорректный номер: {phone}")
        return None


    def filter_unprocessed_numbers(self):
        initial_count = len(self.excel_data_builder.df)
        logging.info(f"Изначально номеров для обработки: {initial_count}")

        self.excel_data_builder.df['Телефон Ответчика'] = self.excel_data_builder.df['Телефон Ответчика'].astype(str)
        self.excel_data_builder.df['Телефон Ответчика'] = self.excel_data_builder.df['Телефон Ответчика'].apply(
            self.normalize_phone_number
        )
        self.excel_data_builder.df.dropna(subset=['Телефон Ответчика'], inplace=True)  # Удалить строки с некорректными номерами
        self.excel_data_builder.df = self.excel_data_builder.df[
            ~self.excel_data_builder.df['Телефон Ответчика'].isin(self.processed_numbers)
        ]
        filtered_count = len(self.excel_data_builder.df)
        logging.info(f"Фильтрация завершена. Осталось для обработки: {filtered_count} из {initial_count}.")

    def get_next_number(self):
        with self.lock:
            if not self.excel_data_builder.df.empty:
                row = self.excel_data_builder.df.iloc[0]
                logging.info(f"Выдан номер для обработки: {row['Телефон Ответчика']}.")
                self.excel_data_builder.df = self.excel_data_builder.df.iloc[1:]
                return row
            else:
                logging.info("Все номера обработаны.")
                self.is_numbers_ended = True
                return None

    def record_valid_number(self, row):
        thread_name = threading.current_thread().name
        normalized_row_number = self.normalize_phone_number(row['Телефон Ответчика'])

        with self.lock:
            if os.path.exists(self.excel_data_builder.output_path):
                current_data = pd.read_excel(self.excel_data_builder.output_path, dtype=str, engine='openpyxl')
            else:
                current_data = pd.DataFrame(columns=self.excel_data_builder.df.columns)

            if normalized_row_number in current_data['Телефон Ответчика'].str.strip().apply(self.normalize_phone_number).values:
                logging.info(f"[{thread_name}] Номер {normalized_row_number} уже существует, пропускаем.")
                return

            row['Телефон Ответчика'] = normalized_row_number
            updated_data = pd.concat([current_data, pd.DataFrame([row])], ignore_index=True)
            updated_data.to_excel(self.excel_data_builder.output_path, index=False, engine='openpyxl')

            self.processed_numbers.add(normalized_row_number)
            logging.info(f"[{thread_name}] Номер {normalized_row_number} добавлен в экспортную таблицу.")


def get_platform_version_from_system_image(system_image):
    if "android-28" in system_image:
        platform_version = "9"
        return platform_version


def process_emulator(
        apk_path: str,
        avd_name: str,
        base_port: int,
        ram_size: str,
        disk_size: str,
        system_image: str,
        platform_version: str,
        avd_ready_timeout: int,
        excel_processor: ThreadSafeExcelProcessor,
        emulator_auth_config_manager: EmulatorAuthConfigManager,
):
    """Запускает эмулятор и проверяет номера на зарегистрированность."""
    try:
        thread_name = threading.current_thread().name

        logging.info(f"[{thread_name}] Начинаем процесс запуска эмулятора {avd_name}...")

        emulator_port = base_port + avd_names.index(avd_name) * 2  # Расчет портов для эмулятора и Appium
        logging.info(f"[{thread_name}] [{avd_name}]: Назначаем порт {emulator_port} для эмулятора {avd_name}...")
        appium_port = 4723 + avd_names.index(avd_name) * 2
        logging.info(f"[{thread_name}] [{avd_name}]: Назначаем порт {appium_port} для Appium-сервера {avd_name}...")



        # Инициализация и запуск эмулятора (если он ранее был запущен - используем snapshot)
        if emulator_auth_config_manager.was_started(avd_name):
            logging.info(f"[{thread_name}] Эмулятор {avd_name} уже был ранее запущен. Попробуем снова его стартовать.")
            if not emulator_manager.start_emulator_with_optional_snapshot(avd_name, emulator_port):
                raise RuntimeError(f"Не удалось перезапустить эмулятор {avd_name}.")
        else:
            # Если эмулятор еще не был создан, создаем его
            if not emulator_manager.start_or_create_emulator(
                    avd_name=avd_name,
                    emulator_port=emulator_port,
                    system_image=system_image,
                    ram_size=ram_size,
                    disk_size=disk_size,
                    avd_ready_timeout=avd_ready_timeout,
            ):
                logging.info(f"[{thread_name}] Эмулятор {avd_name} не был успешно настроен.")
                if not emulator_manager.delete_emulator(avd_name, emulator_port, snapshot_name="authorized"):
                    logging.info(f"[{thread_name}] Эмулятор {avd_name} удалён из-за ошибки настройки.")
                    emulator_auth_config_manager.clear_emulator_data(avd_name)
                raise RuntimeError(f"Не удалось запустить/создать эмулятор {avd_name}.")
            else:
                emulator_auth_config_manager.mark_as_started(avd_name)
                emulator_manager.save_snapshot(
                    avd_name=avd_name,
                    emulator_port=emulator_port,
                    snapshot_name="configured"
                )
                logging.info(f"[{thread_name}] Эмулятор {avd_name} успешно подготовлен к работе!")



        android_driver_manager = AndroidDriverManager(
            local_ip="127.0.0.1",
            port=appium_port,
            emulator_auth_config_manager=emulator_auth_config_manager
        )

        try:
            driver = emulator_manager.setup_driver(
                avd_name=avd_name,
                emulator_port=emulator_port,
                platform_version=platform_version,
                android_driver_manager=android_driver_manager
            )
            if driver is None:
                raise RuntimeError(f"[{thread_name}] Не удалось создать драйвер для {avd_name}.")
            else:
                logging.info(f"[{thread_name}] Драйвер успешно инициализирован для: "
                             f"[avd_name: {avd_name} - emulator_port: {emulator_port}]")
        except Exception as e:
            logging.error(f"[{thread_name}] Ошибка при инициализации драйвера для {avd_name}: {e}")
            return



        tg_mobile_app_automation = TelegramMobileAppAutomation(
            driver=driver,
            avd_name=avd_name,
            excel_processor=excel_processor,
            telegram_app_package="org.telegram.messenger.web",
            emulator_auth_config_manager=emulator_auth_config_manager,
        )

        tg_mobile_app_automation.install_apk(
            app_package=tg_mobile_app_automation.telegram_app_package,
            apk_path=apk_path
        )


        if not emulator_auth_config_manager.is_authorized(avd_name):
            logging.info(f"[{thread_name}] Авторизуйтесь в Telegram на эмуляторе {avd_name} и нажмите Enter для продолжения.")
            input(f"[{thread_name}] Нажмите Enter после завершения авторизации в эмуляторе {avd_name}...\n")
            emulator_manager.save_snapshot(
                avd_name,
                emulator_port,
                snapshot_name="authorized"
            )
            logging.info(f"[{thread_name}] Снепшот 'authorized' в {avd_name} успешно сохранён после авторизации.")
            emulator_auth_config_manager.mark_as_authorized(avd_name)
            logging.info(f"[{thread_name}] Пометил {avd_name} как авторизованный!")


        tg_mobile_app_automation.ensure_is_in_telegram_app()


        while not excel_processor.is_numbers_ended:
            row = excel_processor.get_next_number()
            if row is None:
                break

            phone_number = row['Телефон Ответчика']
            formatted_phone_number = excel_processor.normalize_phone_number(phone_number)
            if not formatted_phone_number:
                logging.warning(f"[{thread_name}] [{avd_name}]: Пропуск некорректного номера: {phone_number}.")
                continue

            logging.info(f"[{thread_name}] [{avd_name}]: Проверка номера: {formatted_phone_number}...")

            if tg_mobile_app_automation.send_message_with_phone_number(formatted_phone_number):
                excel_processor.record_valid_number(row)

            logging.info(f"[{thread_name}] [{avd_name}]: Жмем кнопку 'Назад'")
            driver.press_keycode(AndroidKey.BACK)

    except Exception as ex:
        thread_name = threading.current_thread().name
        logging.error(f"[{thread_name}] [{avd_name}]: Произошла ошибка с эмулятором {avd_name}: {ex}")
    finally:
        thread_name = threading.current_thread().name
        if android_driver_manager:
            android_driver_manager.stop_appium_server()  # Остановить сервер Appium
            logging.info(f"[{thread_name}] Закрыл AppiumServer на порту {appium_port}, связывающий скрипт и driver эмулятора [{avd_name}].")
        if android_driver_manager:
            logging.info(f"[{thread_name}] Очистил ресурсы driver управляющего эмулятором [{avd_name}].")
            android_driver_manager.stop_driver()
        logging.info(f"[{thread_name}] Окончательно завершена обработка в эмуляторе [{avd_name}].")


if __name__ == "__main__":
    thread_name = threading.current_thread().name

    # Параметры
    input_excel_path = os.path.join(DEFAULT_EXCEL_TABLE_DIR, "filled_table.xlsx")
    output_excel_path = os.path.join(DEFAULT_EXCEL_TABLE_DIR, "exported_data.xlsx")

    telegram_app_package = "org.telegram.messenger"
    system_image = "system-images;android-28;google_apis_playstore;x86_64"
    platform_version = get_platform_version_from_system_image(system_image)

    avd_names = ["AVD_DEVICE_1", "AVD_DEVICE_2"]
    # avd_names = ["AVD_DEVICE_1"]
    ram_size = "4096"
    disk_size = "8192M"
    avd_ready_timeout = 600
    base_port = 5554

    emulator_manager = EmulatorManager()    # Инициализируем EmulatorManager
    emulator_auth_config_manager = EmulatorAuthConfigManager()  # Инициализируем EmulatorAuthConfigManager
    excel_processor = ThreadSafeExcelProcessor(input_excel_path, output_excel_path) # Инициализация ExcelDataBuilder

    # Скачивание общего для всех потоков образа один раз перед началом многопоточной обработки
    logging.info(f"[{thread_name}] Проверка и скачивание {system_image} перед запуском потоков...")
    emulator_manager._download_system_image(system_image)
    logging.info(f"[{thread_name}] Образ {system_image} загружен и готов к использованию.")

    apk_path = os.path.join(os.getcwd(), "telegram_apk/Telegram.apk")

    # Многопоточная работа с эмуляторами
    with ThreadPoolExecutor(max_workers=len(avd_names)) as executor:
        for avd_name in avd_names:
            executor.submit(
                process_emulator,
                apk_path=apk_path,
                avd_name=avd_name,
                base_port=base_port,
                ram_size=ram_size,
                disk_size=disk_size,
                system_image=system_image,
                excel_processor=excel_processor,
                platform_version=platform_version,
                avd_ready_timeout=avd_ready_timeout,
                emulator_auth_config_manager=emulator_auth_config_manager,
            )

    logging.info(f"[{thread_name}] Обработка завершена во всех эмуляторах.")
