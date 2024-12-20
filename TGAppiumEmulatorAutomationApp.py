import os
import threading

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

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
        self.is_numbers_ended = False

    def get_next_number(self):
        """Получает следующую строку из таблицы для обработки."""
        with self.lock:
            row = self.excel_data_builder.get_next_row()
            if row is None:
                self.is_numbers_ended = True
            return row

    def record_valid_number(self, row, avd_name):
        """Записывает подтвержденный номер в выходной Excel-файл."""
        thread_name = threading.current_thread().name

        with self.lock:
            logging.info(f"Добавляем строку в экспорт: {row}")
            self.excel_data_builder.export_registered_row(row)
            logging.info(f"[{thread_name}] [{avd_name}] Номер {row['Телефон Ответчика']} добавлен в экспортную таблицу.")

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
            if not phone_number:
                logging.warning(f"[{thread_name}] [{avd_name}]: Пропуск некорректного номера: {phone_number}.")
                continue

            logging.info(f"[{thread_name}] [{avd_name}]: Проверка номера: {phone_number}...")

            if tg_mobile_app_automation.send_message_with_phone_number(phone_number):
                excel_processor.record_valid_number(row, avd_name)

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
