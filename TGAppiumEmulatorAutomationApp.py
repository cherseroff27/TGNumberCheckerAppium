import re
import os
import sys
import time

import threading
from threading import Event

import tkinter as tk

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pandas as pd
from appium.webdriver.extensions.android.nativekey import AndroidKey
from selenium.webdriver.ie.webdriver import WebDriver

from ExcelDataBuilder import ExcelDataBuilder
from TGMobileAppAutomation import TelegramMobileAppAutomation
from EmulatorAuthConfigManager import EmulatorAuthConfigManager
from AndroidDriverManager import AndroidDriverManager
from EmulatorManager import EmulatorManager

from TelegramCheckerUI import TelegramCheckerUI
from TelegramCheckerUILogic import TelegramCheckerUILogic

from TelegramApkVersionManager import TelegramApkVersionManager

from EmulatorAuthWindowManager import EmulatorAuthWindowManager

from MobileElementsHandler import MobileElementsHandler as Meh

from logger_config import Logger

logger = Logger.get_logger(__name__)


DEFAULT_EXCEL_TABLE_DIR = os.path.abspath("excel_tables_dir")


class ThreadSafeExcelProcessor:
    def __init__(self, input_path, output_path):
        self.excel_data_builder = ExcelDataBuilder(input_path, output_path)
        self.lock = Lock()
        self.processed_numbers = self.load_processed_numbers()
        logger.info(f"Загружено {len(self.processed_numbers)} обработанных номеров.")
        self.is_numbers_ended = False

    def load_processed_numbers(self):
        if os.path.exists(self.excel_data_builder.output_path):
            try:
                processed_data = pd.read_excel(self.excel_data_builder.output_path, dtype=str, engine='openpyxl')
                return {self.normalize_phone_number(num) for num in processed_data['Телефон Ответчика']}
            except Exception as e:
                logger.exception(f"Ошибка при загрузке экспортной таблицы: {e}")
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
        logger.warning(f"Некорректный номер: {phone}")
        return None


    def filter_unprocessed_numbers(self):
        initial_count = len(self.excel_data_builder.df)
        logger.info(f"Изначально номеров для обработки: {initial_count}")

        self.excel_data_builder.df['Телефон Ответчика'] = self.excel_data_builder.df['Телефон Ответчика'].astype(str)
        self.excel_data_builder.df['Телефон Ответчика'] = self.excel_data_builder.df['Телефон Ответчика'].apply(
            self.normalize_phone_number
        )
        self.excel_data_builder.df.dropna(subset=['Телефон Ответчика'], inplace=True)  # Удалить строки с некорректными номерами
        self.excel_data_builder.df = self.excel_data_builder.df[
            ~self.excel_data_builder.df['Телефон Ответчика'].isin(self.processed_numbers)
        ]
        filtered_count = len(self.excel_data_builder.df)
        logger.info(f"Фильтрация завершена. Осталось для обработки: {filtered_count} из {initial_count}.")


    def get_next_number(self, thread_name, avd_name):
        with self.lock:
            if not self.excel_data_builder.df.empty:
                row = self.excel_data_builder.df.iloc[0]
                logger.debug(f"[{thread_name}] [{avd_name}]: Выдан номер для обработки: {row['Телефон Ответчика']}.")
                self.excel_data_builder.df = self.excel_data_builder.df.iloc[1:]
                return row
            else:
                logger.info("Все номера обработаны.")
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
                logger.debug(f"[{thread_name}] Номер {normalized_row_number} уже существует, пропускаем.")
                return

            row['Телефон Ответчика'] = normalized_row_number
            updated_data = pd.concat([current_data, pd.DataFrame([row])], ignore_index=True)
            updated_data.to_excel(self.excel_data_builder.output_path, index=False, engine='openpyxl')

            self.processed_numbers.add(normalized_row_number)
            logger.info(f"[{thread_name}] Номер {normalized_row_number} добавлен в экспортную таблицу.")

class TGAppiumEmulatorAutomationApp:
    def __init__(self):
        self.terminate_flag = Event()
        self.root = tk.Tk()
        self.emulator_auth_window_manager = EmulatorAuthWindowManager(self.root)

        self.emulator_manager = EmulatorManager()    # Инициализируем EmulatorManager

        self.emulator_auth_config_manager = EmulatorAuthConfigManager()
        self.logic = TelegramCheckerUILogic(
            config_file=EmulatorAuthConfigManager.CONFIG_FILE,
            default_excel_dir=DEFAULT_EXCEL_TABLE_DIR,
            emulator_auth_config_manager=self.emulator_auth_config_manager,
            emulator_manager= self.emulator_manager,
        )
        self.ui = TelegramCheckerUI(self.root, self.logic, self)
        self.ui.refresh_excel_table()


    def run_multithreaded_automation(self):
        thread_name = threading.current_thread().name

        apk_version_manager = TelegramApkVersionManager(telegram_app_package="org.telegram.messenger.web")
        apk_url = "https://telegram.org/dl/android/apk"
        project_dir = os.path.dirname(os.path.abspath(__file__))
        apk_save_dir = os.path.join(project_dir, "telegram_apk")
        apk_name = "Telegram"
        downloaded_apk_path = apk_version_manager.download_latest_telegram_apk(apk_url, apk_save_dir, apk_name)
        logger.info(f"Актуальная версия Telegram сохранена в: {downloaded_apk_path}")

        avd_names = [f"AVD_DEVICE_{i + 1}" for i in range(self.ui.num_threads.get())]

        input_excel_path = app.ui.source_excel_file_path.get()
        logger.info(f"Исходный файл таблицы: {input_excel_path}")
        output_excel_path = app.ui.export_table_path.get()
        logger.info(f"Экспортный файл таблицы: {output_excel_path}")

        ram_size = "1024"
        disk_size = "2048M"
        avd_ready_timeout = 600
        base_port = 5554


        emulator_auth_config_manager = EmulatorAuthConfigManager()  # Инициализируем EmulatorAuthConfigManager
        excel_processor = ThreadSafeExcelProcessor(input_excel_path, output_excel_path) # Инициализация ExcelDataBuilder

        system_image = "system-images;android-22;google_apis;x86"
        platform_version = self.get_platform_version_from_system_image(system_image)

        # Скачивание общего для всех потоков образа один раз перед началом многопоточной обработки
        logger.info(f"[{thread_name}] Проверка и скачивание {system_image} перед запуском потоков...")
        self.emulator_manager.download_system_image(system_image)
        logger.info(f"[{thread_name}] Образ {system_image} загружен и готов к использованию.")

        apk_path = os.path.join(os.getcwd(), "telegram_apk/Telegram.apk")

        # Многопоточная работа с эмуляторами
        with ThreadPoolExecutor(max_workers=len(avd_names)) as executor:
            futures = []
            for avd_name in avd_names:
                future =executor.submit(
                    self.process_emulator,
                    apk_path=apk_path,
                    avd_name=avd_name,
                    avd_names=avd_names,
                    base_port=base_port,
                    ram_size=ram_size,
                    disk_size=disk_size,
                    system_image=system_image,
                    emulator_manager=self.emulator_manager,
                    excel_processor=excel_processor,
                    platform_version=platform_version,
                    avd_ready_timeout=avd_ready_timeout,
                    apk_version_manager=apk_version_manager,
                    emulator_auth_config_manager=emulator_auth_config_manager,
                )
                futures.append(future)
            # Ждём завершения потоков
            for future in futures:
                future.result()

        logger.info(f"[{thread_name}] Обработка завершена во всех эмуляторах.")


    def process_emulator(
            self,
            apk_path: str,
            avd_name: str,
            avd_names: list[str],
            base_port: int,
            ram_size: str,
            disk_size: str,
            system_image: str,
            platform_version: str,
            avd_ready_timeout: int,
            emulator_manager: EmulatorManager,
            excel_processor: ThreadSafeExcelProcessor,
            apk_version_manager: TelegramApkVersionManager,
            emulator_auth_config_manager: EmulatorAuthConfigManager,
    ):
        """Запускает эмулятор и проверяет номера на зарегистрированность."""
        thread_name = None
        android_driver_manager = None
        appium_port = None
        emulator_port = None

        try:
            thread_name = threading.current_thread().name

            logger.info(f"[{thread_name}] Начинаем процесс запуска эмулятора {avd_name}...")

            emulator_port, appium_port = AndroidDriverManager.setup_connection_data(
                base_port=base_port,
                avd_names=avd_names,
                avd_name=avd_name
            )

            # Проверка флага перед запуском длительных операций
            if self.terminate_flag.is_set():
                self.cleanup(thread_name=thread_name, android_driver_manager=android_driver_manager, avd_name=avd_name,
                             appium_port=appium_port, emulator_manager=emulator_manager, emulator_port=emulator_port, ui=app.ui)

            # Инициализация и запуск эмулятора (если он ранее был запущен - используем snapshot)
            if emulator_auth_config_manager.was_started(avd_name):
                logger.info(f"[{thread_name}] Эмулятор {avd_name} уже был ранее запущен. Попробуем снова его стартовать.")
                if not emulator_manager.start_emulator_with_optional_snapshot(
                        avd_name=avd_name,
                        emulator_port=emulator_port,
                        avd_ready_timeout=avd_ready_timeout
                ):
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
                    logger.info(f"[{thread_name}] Эмулятор {avd_name} не был успешно настроен.")
                    if not emulator_manager.delete_emulator(avd_name, emulator_port, snapshot_name="authorized"):
                        logger.info(f"[{thread_name}] Эмулятор {avd_name} удалён из-за ошибки настройки.")
                        emulator_auth_config_manager.clear_emulator_data(avd_name)
                    raise RuntimeError(f"Не удалось запустить/создать эмулятор {avd_name}.")
                else:
                    logger.info(f"[{thread_name}] Эмулятор {avd_name} успешно подготовлен к работе!")


            # Проверка перед следующими шагами
            if self.terminate_flag.is_set():
                self.cleanup(thread_name=thread_name, android_driver_manager=android_driver_manager, avd_name=avd_name,
                             appium_port=appium_port, emulator_manager=emulator_manager, emulator_port=emulator_port, ui=app.ui)

            android_driver_manager = AndroidDriverManager(
                local_ip="127.0.0.1",
                port=appium_port,
                emulator_auth_config_manager=emulator_auth_config_manager
            )

            driver = self.setup_driver(
                avd_name=avd_name,
                emulator_port=emulator_port,
                emulator_manager=emulator_manager,
                thread_name=thread_name,
                android_driver_manager=android_driver_manager,
                platform_version=platform_version
            )



            while not emulator_auth_config_manager.was_started(avd_name):
                logger.info(f"[{thread_name}] [{avd_name}] Запуск  отслеживания приветственного окна Android.")
                self.monitor_initial_window_and_mark_as_started(
                    driver=driver,
                    thread_name=thread_name,
                    avd_name=avd_name,
                    emulator_auth_config_manager=emulator_auth_config_manager,
                    emulator_manager=emulator_manager,
                    emulator_port=emulator_port
                )



            tg_mobile_app_automation = TelegramMobileAppAutomation(
                driver=driver,
                avd_name=avd_name,
                excel_processor=excel_processor,
                telegram_app_package="org.telegram.messenger.web",
                emulator_auth_config_manager=emulator_auth_config_manager,
            )



            tg_mobile_app_automation.install_or_update_telegram_apk(
                apk_version_manager=apk_version_manager,
                apk_path=apk_path,
                emulator_port=emulator_port
            )


            while not emulator_auth_config_manager.is_authorized(avd_name):
                auth_event = self.emulator_auth_window_manager.show_auth_window(avd_name)
                auth_event.wait()  # Ожидание, пока пользователь не подтвердит авторизацию

                emulator_manager.save_snapshot(
                    avd_name,
                    emulator_port,
                    snapshot_name="authorized"
                )
                logger.info(f"[{thread_name}] Снепшот 'authorized' в {avd_name} успешно сохранён после авторизации.")
                time.sleep(3)
                emulator_manager.wait_for_emulator_ready(
                    avd_name=avd_name,
                    emulator_port=emulator_port,
                    avd_ready_timeout=avd_ready_timeout
                )
                emulator_auth_config_manager.mark_as_authorized(avd_name)
                logger.info(f"[{thread_name}] Пометил {avd_name} в конфиге как 'authorized'!")

                time.sleep(3)

                tg_mobile_app_automation.prepare_telegram_app()

                if not tg_mobile_app_automation.ensure_is_in_telegram_app():
                    emulator_auth_config_manager.reset_authorization(avd_name)


            tg_mobile_app_automation.prepare_telegram_app()

            if not tg_mobile_app_automation.ensure_is_in_telegram_app():
                emulator_auth_config_manager.reset_authorization(avd_name)


            while not excel_processor.is_numbers_ended:
                if self.terminate_flag.is_set():
                    break  # Прерываем цикл, если флаг установлен

                row = excel_processor.get_next_number(thread_name=thread_name, avd_name=avd_name)
                if row is None:
                    break

                phone_number = row['Телефон Ответчика']
                formatted_phone_number = excel_processor.normalize_phone_number(phone_number)
                if not formatted_phone_number:
                    logger.warning(f"[{thread_name}] [{avd_name}]: Пропуск некорректного номера: {phone_number}.")
                    continue

                logger.info(f"[{thread_name}] [{avd_name}]: Проверка номера: {formatted_phone_number}...")

                if tg_mobile_app_automation.send_message_with_phone_number(formatted_phone_number):
                    excel_processor.record_valid_number(row)

                logger.info(f"[{thread_name}] [{avd_name}]: Жмем кнопку 'Назад'")
                driver.press_keycode(AndroidKey.BACK)

        except Exception as ex:
            thread_name = threading.current_thread().name
            logger.error(f"[{thread_name}] [{avd_name}]: Произошла ошибка с эмулятором {avd_name}: {ex}")
        finally:
            self.cleanup(thread_name=thread_name, android_driver_manager=android_driver_manager, avd_name=avd_name,
                         appium_port=appium_port, emulator_manager=emulator_manager, emulator_port=emulator_port, ui=app.ui)

            self.terminate_program(self.ui)

        self.cleanup(
            thread_name=thread_name,
            android_driver_manager=android_driver_manager,
            avd_name=avd_name,
            appium_port=appium_port,
            emulator_manager=emulator_manager,
            emulator_port=emulator_port,
            ui=app.ui
        )

        self.terminate_program(self.ui)

    @staticmethod
    def monitor_initial_window_and_mark_as_started(
            driver: WebDriver,
            thread_name: str,
            avd_name: str,
            emulator_auth_config_manager: EmulatorAuthConfigManager,
            emulator_manager: EmulatorManager,
            emulator_port: int,
    ):
        while True:
            try:
                logger.info(f"[{thread_name}] [{avd_name}]: Мониторим наличие приветственного системного окна.")
                skip_button_locator = "//android.widget.Button[@text='GOT IT']"
                skip_button_element = Meh.wait_for_element_xpath(
                    skip_button_locator,
                    driver=driver,
                    timeout=4,
                    interval=2,
                    enable_logger=False
                )
                if skip_button_element:
                    logger.info(f"[{thread_name}] [{avd_name}]: Приветственное системное окно найдено. Пытаемся закрыть...")
                    skip_button_element.click()
                    logger.info(f"[{thread_name}] [{avd_name}]: Приветственное системное окно пропущено.")
                    emulator_auth_config_manager.mark_as_started(avd_name)
                    logger.info(f"[{thread_name}]: Пометил эмулятор [{avd_name}] в конфиге как запущенный.")

                    time.sleep(1)

                    emulator_manager.save_snapshot(
                        avd_name=avd_name,
                        emulator_port=emulator_port,
                        snapshot_name="configured"
                    )

                    break
            except Exception as ex:
                logger.info(f"[{thread_name}] [{avd_name}]: Приветственное системное окно не обнаружено или уже пропущено: ", ex)
            time.sleep(5)  # Делает проверку раз в 5 секунд


    @staticmethod
    def setup_driver(avd_name, emulator_manager, emulator_port, platform_version, android_driver_manager, thread_name):
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
                logger.info(f"[{thread_name}] Драйвер успешно инициализирован для: "
                             f"[avd_name: {avd_name} - emulator_port: {emulator_port}]")

            return driver
        except Exception as e:
            logger.error(f"[{thread_name}] Ошибка при инициализации драйвера для {avd_name}: {e}")
            return
    @staticmethod
    def get_platform_version_from_system_image(system_image):
        if "android-28" in system_image:
            platform_version = "9"
            return platform_version
        if "android-22" in system_image:
            platform_version = "5.1"
            return platform_version


    @staticmethod
    def cleanup(thread_name, android_driver_manager, avd_name, appium_port, emulator_manager, emulator_port, ui):
        try:
            ui.disable_terminate_button()
            logger.info("Запущен процесс очистки ресурсов перед завершением программы.")
            if android_driver_manager:
                android_driver_manager.stop_driver()
                logger.info(f"[{thread_name}] Очистил ресурсы driver, управляющего эмулятором [{avd_name}] на порту [{emulator_port}].")

                android_driver_manager.stop_appium_server()
                logger.info(f"[{thread_name}] Закрыл AppiumServer на порту [{appium_port}], связывающий скрипт и driver эмулятора [{avd_name}].")

                logger.info(f"Окончательно завершена обработка в эмуляторе [{avd_name}].")

            if emulator_manager:
                emulator_manager.close_emulator(
                    thread_name=thread_name,
                    avd_name=avd_name,
                    emulator_port=emulator_port,
                )
        except Exception as e:
            logger.error(f"[{thread_name}] Ошибка при очистке ресурсов: {e}")
        finally:
            logger.info(f"[{thread_name}] Завершение программы.")
            sys.exit(0)


    def terminate_program(self, ui):
        logger.info("Завершаем работу приложения...")
        ui.disable_terminate_button()
        self.terminate_flag.set()
        logger.info("Приложение вскоре будет завершено... Очистка ресурсов, закрытие эмуляторов...")
        time.sleep(5)


if __name__ == "__main__":
    app = TGAppiumEmulatorAutomationApp()
    app.root.mainloop()
