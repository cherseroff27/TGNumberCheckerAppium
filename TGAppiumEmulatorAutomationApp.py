import os
import threading
import time

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from ExcelDataBuilder import ExcelDataBuilder
from TGMobileAppAutomation import TelegramMobileAppAutomation
from EmulatorAuthConfigManager import EmulatorAuthConfigManager
from AndroidDriverManager import AndroidDriverManager
from EmulatorManager import EmulatorManager

from appium import webdriver

from manual_script_control import ManualScriptControl

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
        self.is_numbers_ended = False

    def get_next_number(self):
        """Получает следующую строку из таблицы для обработки."""
        with self.lock:
            if not self.excel_data_builder.df.empty:
                row = self.excel_data_builder.df.iloc[0]
                logging.debug(f"Выдан номер для обработки: {row['Телефон Ответчика']}.")
                self.excel_data_builder.df = self.excel_data_builder.df.iloc[1:]     # Удаляем строку из DataFrame
                return row
            else:
                logging.info("DataFrame пуст, все номера обработаны.")
                self.is_numbers_ended = True
                return None

    def record_valid_number(self, row, avd_name):
        """Записывает подтвержденный номер в выходной Excel-файл."""
        thread_name = threading.current_thread().name
        with self.lock:
            number = row['Телефон Ответчика']
            self.excel_data_builder.export_registered_contacts([row['Телефон Ответчика']])
            logging.info(f"[{thread_name}] [{avd_name}] Номер {number} добавлен в экспортную таблицу.")


def get_platform_version_from_system_image(system_image):
    if "android-28" in system_image:
        platform_version = "9"
        return platform_version


def process_emulator(
        avd_name: str,
        emulator_auth_config_manager: EmulatorAuthConfigManager,
        platform_version: str,
        excel_processor: ThreadSafeExcelProcessor,
        system_image: str,
        ram_size: str,
        disk_size: str,
        avd_ready_timeout: int,
        base_port: int,
):
    """Запускает эмулятор и проверяет номера на зарегистрированность."""
    try:
        thread_name = threading.current_thread().name
        logging.info(f"[{thread_name}] Начинаем процесс запуска эмулятора {avd_name}...")


        emulator_port = base_port + avd_names.index(avd_name) * 2  # Расчет портов для эмулятора и Appium
        logging.info(f"[{thread_name}] [{avd_name}]: Назначаем порт {emulator_port} для эмулятора {avd_name}...")
        appium_port = 4723 + avd_names.index(avd_name) * 2
        logging.info(f"[{thread_name}] [{avd_name}]: Назначаем порт {appium_port} для Appium-сервера {avd_name}...")

        # Инициализация и запуск эмулятора
        if emulator_auth_config_manager.was_started(avd_name):
            logging.info(f"[{thread_name}] Эмулятор {avd_name} уже был ранее запущен. Попробуем снова его стартовать.")
            if not emulator_manager.start_emulator_with_snapshot(avd_name, emulator_port, snapshot_name="authorized"):
                raise RuntimeError(f"Не удалось перезапустить эмулятор {avd_name}.")
            emulator_manager.wait_for_emulator_ready(emulator_port)
            time.sleep(3)
        else:
            # Если эмулятор еще не был создан, создаем его
            if not emulator_manager.start_or_create_emulator(
                    avd_name=avd_name,
                    port=emulator_port,
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
                emulator_manager.save_snapshot(avd_name, emulator_port, snapshot_name="configured")
                logging.info(f"[{thread_name}] Эмулятор {avd_name} успешно подготовлен к работе!")
                return



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
                logging.info(f"[{thread_name}] Драйвер успешно инициализирован для:\n"
                             f"avd_name: {avd_name} - emulator_port: {emulator_port}")
        except Exception as e:
            logging.error(f"[{thread_name}] Ошибка при инициализации драйвера для {avd_name}: {e}")
            return



        if not emulator_auth_config_manager.is_authorized(avd_name):
            ManualScriptControl.wait_for_user_input(f"Авторизуйтесь в Telegram на эмуляторе {avd_name} и нажмите Enter для продолжения.")

            emulator_auth_config_manager.mark_as_authorized(avd_name)
            emulator_manager.save_snapshot(avd_name, emulator_port, snapshot_name="authorized")

        telegram_mobile_app_automation = TelegramMobileAppAutomation(
            driver=driver,
            avd_name=avd_name,
            emulator_auth_config_manager=emulator_auth_config_manager,
            excel_processor=excel_processor,
        )


        while not excel_processor.is_numbers_ended:
            row = excel_processor.get_next_number()
            if row is None:
                break

            phone_number = row['Телефон Ответчика']
            logging.info(f"[{thread_name}] [{avd_name}]: Проверка номера: {phone_number}...")

            if telegram_mobile_app_automation.send_message_with_phone_number(phone_number):
                excel_processor.record_valid_number(row, avd_name)
                logging.info(f"[{thread_name}] [{avd_name}]: Номер {phone_number} зарегистрирован.")
            else:
                logging.info(f"[{thread_name}] [{avd_name}]: Номер {phone_number} не зарегистрирован.")

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
    input_excel_path = os.path.join(DEFAULT_EXCEL_TABLE_DIR, "random_excel_data.xlsx")
    output_excel_path = os.path.join(DEFAULT_EXCEL_TABLE_DIR, "exported_data.xlsx")

    telegram_app_package = "org.telegram.messenger"
    system_image = "system-images;android-28;google_apis_playstore;x86_64"
    platform_version = get_platform_version_from_system_image(system_image)

    avd_names = ["AVD_DEVICE_1", "AVD_DEVICE_2"]
    # avd_names = ["AVD_DEVICE_1"]
    ram_size = "2048"
    disk_size = "8192M"
    avd_ready_timeout = 600
    base_port = 5554

    emulator_manager = EmulatorManager()    # Инициализируем EmulatorManager
    emulator_auth_config_manager = EmulatorAuthConfigManager()  # Инициализируем EmulatorAuthConfigManager
    excel_processor = ThreadSafeExcelProcessor(input_excel_path, output_excel_path) # Инициализация ExcelDataBuilder

    # Скачивание общего для всех потоков образа один раз перед началом многопоточной обработки
    logging.info(f"[{thread_name}] Проверка и скачивание {system_image} перед запуском потоков...")
    emulator_manager._download_system_image(system_image)

    # Многопоточная работа с эмуляторами
    with ThreadPoolExecutor(max_workers=len(avd_names)) as executor:
        for avd_name in avd_names:
            executor.submit(
                process_emulator,
                avd_name,
                emulator_auth_config_manager,
                platform_version,
                excel_processor,
                system_image,
                ram_size,
                disk_size,
                avd_ready_timeout,
                base_port,
            )

    print(f"[{thread_name}] Обработка завершена во всех эмуляторах.")