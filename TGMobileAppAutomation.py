import threading
import time
import logging

from appium.webdriver.extensions.android.nativekey import AndroidKey
from manual_script_control import ManualScriptControl
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver import ActionChains
from MobileElementsHandler import MobileElementsHandler as Meh

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


class TelegramMobileAppAutomation:
    def __init__(self, driver, avd_name, emulator_auth_config_manager, excel_processor, telegram_app_package):
        self.driver = driver
        self.emulator_auth_config_manager = emulator_auth_config_manager
        self.excel_processor = excel_processor
        self.avd_name = avd_name
        self.telegram_app_package = telegram_app_package
        self.actions = ActionChains(driver)


    def prepare_telegram_app(self):
        thread_name = threading.current_thread().name

        try:
            # Проверка текущего состояния и возвращение на главный экран
            current_activity = self.driver.current_activity
            logging.info(f"[{thread_name}] [{self.avd_name}]: Текущее Activity: {current_activity}")

            if "org.telegram.messenger" not in current_activity:
                logging.info(f"[{thread_name}] [{self.avd_name}]: Мы не в Telegram. Проверяем, где мы находимся.")

                # Завершаем текущее приложение
                logging.info(f"[{thread_name}] [{self.avd_name}]: Завершаем текущее приложение.")
                self.driver.press_keycode(AndroidKey.HOME)
                time.sleep(2)

                # Проверяем главный экран
                is_home_screen = self.is_on_home_screen()
                if not is_home_screen:
                    logging.info(f"[{thread_name}] [{self.avd_name}]: Возвращаемся на главный экран рабочего стола.")
                    self.driver.press_keycode(AndroidKey.HOME)
                    time.sleep(2)

            # Открытие приложения Telegram
            logging.info(f"[{thread_name}] [{self.avd_name}]: Открываем приложение Telegram.")
            self.driver.activate_app(self.telegram_app_package)

            # Ожидание загрузки Telegram (appActivity содержит "org.telegram.messenger")
            self.wait_for_activity_contains("org.telegram.messenger", timeout=15)
            logging.info(f"[{thread_name}] [{self.avd_name}]: Telegram успешно запущен.")

            # Закрываем Telegram
            logging.info(f"[{thread_name}] [{self.avd_name}]: Закрываем приложение Telegram.")
            self.driver.terminate_app(self.telegram_app_package)
            time.sleep(2)

            # Повторное открытие Telegram
            logging.info(f"[{thread_name}] [{self.avd_name}]: Повторное открытие приложения Telegram.")
            self.driver.activate_app(self.telegram_app_package)

            # Ожидание появления главного экрана Telegram (appActivity с "DefaultIcon")
            self.wait_for_activity_contains("org.telegram.messenger.DefaultIcon", timeout=15)
            logging.info(f"[{thread_name}] [{self.avd_name}]: Главный экран Telegram загружен.")

        except Exception as e:
            logging.error(f"[{thread_name}] [{self.avd_name}]: Ошибка при подготовке приложения Telegram: {e}")
            raise

    def is_on_home_screen(self):
        """
        Проверяет, находимся ли мы на главном экране рабочего стола.
        """
        thread_name = threading.current_thread().name

        try:
            current_activity = self.driver.current_activity
            logging.info(f"[{thread_name}] [{self.avd_name}]: Проверяем, на главном ли экране: {current_activity}")
            # Замените это значение на соответствующее вашей версии Android
            return current_activity == "com.android.launcher3.Launcher"
        except Exception as e:
            logging.error(f"[{thread_name}] [{self.avd_name}]: Ошибка при проверке главного экрана: {e}")
            return False


    def wait_for_activity_contains(self, activity_substring, timeout=15):
        """
        Ожидает, пока текущее activity не будет содержать указанную подстроку.
        """
        thread_name = threading.current_thread().name

        start_time = time.time()
        while time.time() - start_time < timeout:
            current_activity = self.driver.current_activity
            if activity_substring in current_activity:
                return True
            time.sleep(1)
        raise TimeoutError(f"[{thread_name}] [{self.avd_name}]: Activity с '{activity_substring}' не загрузилось за {timeout} секунд.")



    def ensure_is_in_telegram_app(self):
        thread_name = threading.current_thread().name

        try:
            self.prepare_telegram_app()
            logging.info(f"[{thread_name}] [{self.avd_name}]: Убедились, что приложение Telegram открыто.")
        except Exception as e:
            logging.error(f"[{thread_name}] [{self.avd_name}]: Ошибка при попытке открыть Telegram: {e}")
            raise


    def install_apk(self, app_package, apk_path):
        thread_name = threading.current_thread().name

        while not self.driver.is_app_installed(app_package):
            logging.info(f"[{thread_name}] [{self.avd_name}] Приложение {app_package} еще не установлено, пробуем установить...")
            self.driver.install_app(apk_path)

        logging.info(f"[{thread_name}] [{self.avd_name}] Приложение {app_package} успешно установлено.")


    def send_message_with_phone_number(self, phone_number):
        thread_name = threading.current_thread().name

        # Запуск настроек для теста
        self.driver.activate_app("com.android.settings")

        ManualScriptControl.wait_for_user_input(f"[{thread_name}] [{self.avd_name}]: Загрузился в эмулятор и открыл настройки.\n")

        self.ensure_is_in_telegram_app()

        try:
            navigation_menu_locator = "//android.widget.ImageView[@content-desc='Открыть меню навигации']"
            navigation_menu_el = Meh.wait_for_element_xpath(
                navigation_menu_locator, driver=self.driver, timeout=15)

            navigation_menu_el.click()

            print(f"[{thread_name}] [{self.avd_name}]: Кнопка меню навигации успешно нажата!")



            saved_messages_locator = "(//android.widget.TextView[@text='Избранное'])[1]"
            saved_messages_el = Meh.wait_for_element_xpath(
                saved_messages_locator, driver=self.driver, timeout=15)


            saved_messages_el.click()

            print(f"[{self.avd_name}]: Кнопка 'Избранное' успешно нажата!")



            print(f"[{self.avd_name}]: Пробуем проверить номер {phone_number}.")

            message_field_locator = "//android.widget.EditText[@text='Сообщение']"
            message_field_el = Meh.wait_for_element_xpath(
                message_field_locator, driver=self.driver, timeout=15)

            message_field_el.click()
            time.sleep(0.5)

            message_field_el.send_keys(phone_number)
            time.sleep(0.5)



            send_button_locator = "//android.view.View[@content-desc='Отправить']"
            send_button_el = Meh.wait_for_element_xpath(
                send_button_locator, driver=self.driver, timeout=15)

            send_button_el.click()

            current_number_message_locator = f"//android.view.ViewGroup[contains(@text, '{phone_number}')][last()]"
            current_number_message_el = Meh.wait_for_element_xpath(
                current_number_message_locator, driver=self.driver, timeout=15)

            # Получение координат элемента
            rect = current_number_message_el.rect
            print(rect)
            center_x = rect['x'] + (rect['width'] // 2)
            center_y = rect['y'] + (rect['height'] // 2)

            shifted_x = int(center_x + center_x * 0.25)
            shifted_y = int(center_y + center_y * 0.05)

            print(f"[{self.avd_name}]: Клик по центру элемента: x={shifted_x}, y={shifted_y}") # Заменить shifted_y на center_y, если не заработает.


            # Выполнение клика по центру элемента
            self.actions.w3c_actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
            self.actions.w3c_actions.pointer_action.move_to_location(shifted_x, center_y)
            self.actions.w3c_actions.pointer_action.pointer_down()
            self.actions.w3c_actions.pointer_action.pointer_up()
            self.actions.perform()

            show_profile_btn_locator = "//android.widget.TextView[contains(@text, 'Перейти в профиль')]"
            profile_doesnt_exist_locator = "//android.widget.TextView[contains(@text, 'Номер не зарегистрирован в Telegram')]"


            element = Meh.wait_for_element_xpath(
                profile_doesnt_exist_locator, show_profile_btn_locator, driver=self.driver, timeout=15)


            if "Перейти в профиль" in element.get_attribute("text"):
                print(f"[{self.avd_name}]: Номер {phone_number} зарегистрирован в Telegram.")
            elif "Номер не зарегистрирован в Telegram" in element.get_attribute("text"):
                print(f"[{self.avd_name}]: Номер {phone_number} не зарегистрирован в Telegram.")

        except Exception as ex:
            self.driver.stop_driver()
            print(f"[{self.avd_name}]: Произошла ошибка в процессе автоматизации: {ex}")


    def authorize_if_needed(self):
        thread_name = threading.current_thread().name

        try:
            if not self.emulator_auth_config_manager.is_authorized(self.avd_name):
                ManualScriptControl.wait_for_user_input(f"[{thread_name}] [{self.avd_name}]: Авторизуйтесь в Telegram Web и нажмите Enter для продолжения.")
        except Exception as e:
            print(f"[{thread_name}] [{self.avd_name}]: Ошибка авторизации для эмулятора: {e}")

