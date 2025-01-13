import subprocess
import threading
from threading import Lock
import time

from appium.webdriver.extensions.android.nativekey import AndroidKey
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver import ActionChains

from TelegramApkVersionManager import TelegramApkVersionManager

from MobileElementsHandler import MobileElementsHandler as Meh

from logger_config import Logger
logger = Logger.get_logger(__name__)


class TelegramMobileAppAutomation:
    def __init__(self, driver, avd_name, emulator_auth_config_manager, excel_processor, telegram_app_package):
        self.driver = driver
        self.emulator_auth_config_manager = emulator_auth_config_manager
        self.excel_processor = excel_processor
        self.avd_name = avd_name
        self.telegram_app_package = telegram_app_package
        self.actions = ActionChains(driver)
        self.lock = Lock()
        self.was_entered_saved_messages_page = False


    def prepare_telegram_app(self):
        thread_name = threading.current_thread().name
        while True:
            try:
                # Проверка текущего состояния и возвращение на главный экран
                current_activity = self.driver.current_activity
                logger.info(f"[{thread_name}] [{self.avd_name}]: Текущее Activity: {current_activity}")

                if "org.telegram.messenger" not in current_activity:
                    logger.info(f"[{thread_name}] [{self.avd_name}]: Мы не в Telegram. Проверяем, где мы находимся.")

                    # Завершаем текущее приложение
                    logger.info(f"[{thread_name}] [{self.avd_name}]: Завершаем текущее приложение.")
                    self.driver.press_keycode(AndroidKey.HOME)
                    time.sleep(3)

                    # Проверяем главный экран
                    is_home_screen = self.is_on_home_screen()
                    if not is_home_screen:
                        logger.info(f"[{thread_name}] [{self.avd_name}]: Возвращаемся на главный экран рабочего стола.")
                        self.driver.press_keycode(AndroidKey.HOME)
                        time.sleep(3)

                # Открытие приложения Telegram
                logger.info(f"[{thread_name}] [{self.avd_name}]: Открываем приложение Telegram.")
                self.driver.activate_app(self.telegram_app_package)

                # Ожидание загрузки Telegram (appActivity содержит "org.telegram.messenger")
                self.wait_for_activity_contains("org.telegram.messenger", timeout=30)
                logger.info(f"[{thread_name}] [{self.avd_name}]: Telegram успешно запущен.")

                # Закрываем Telegram
                logger.info(f"[{thread_name}] [{self.avd_name}]: Закрываем приложение Telegram.")
                self.driver.terminate_app(self.telegram_app_package)
                time.sleep(3)

                # Повторное открытие Telegram
                logger.info(f"[{thread_name}] [{self.avd_name}]: Повторное открытие приложения Telegram.")
                self.driver.activate_app(self.telegram_app_package)

                # Ожидание появления главного экрана Telegram (appActivity с "DefaultIcon")
                self.wait_for_activity_contains("org.telegram.messenger.DefaultIcon", timeout=30)
                logger.info(f"[{thread_name}] [{self.avd_name}]: Главный экран Telegram загружен.")

                return True
            except Exception as e:
                logger.error(f"[{thread_name}] [{self.avd_name}]: Ошибка при подготовке приложения Telegram: {e}")
                return False



    def is_on_home_screen(self):
        """
        Проверяет, находимся ли мы на главном экране рабочего стола.
        """
        thread_name = threading.current_thread().name

        try:
            current_activity = self.driver.current_activity
            logger.info(f"[{thread_name}] [{self.avd_name}]: Проверяем, на главном ли экране: {current_activity}")
            # Замените это значение на соответствующее вашей версии Android
            return "com.google.android" in current_activity
        except Exception as e:
            logger.error(f"[{thread_name}] [{self.avd_name}]: Ошибка при проверке главного экрана: {e}")
            return False


    def wait_for_activity_contains(self, activity_substring, timeout=30):
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


    def check_if_not_authorized(self, thread_name):

        start_messaging_button_locator_ru = "//android.widget.TextView[@text='Start Messaging']"
        start_messaging_button_locator_en = "//android.widget.TextView[@text='Начать общение']"
        navigation_menu_locator_ru = "//android.widget.ImageView[@content-desc='Открыть меню навигации']"
        navigation_menu_locator_en = "//android.widget.ImageView[@content-desc='Open navigation menu']"
        found_element = Meh.wait_for_element_xpath(
            start_messaging_button_locator_ru,
            start_messaging_button_locator_en,
            navigation_menu_locator_ru,
            navigation_menu_locator_en,
            driver=self.driver,
            timeout=10,
            interval=2
        )

        while True:
            text_attribute = found_element.get_attribute("text")
            content_desc_attribute = found_element.get_attribute("content-desc")
            if text_attribute and "Start Messaging" in text_attribute or "Начать общение" in text_attribute:
                logger.error(f"[{thread_name}] [{self.avd_name}]: Вы так и не авторизовались в Telegram вручную!")
                return False
            elif (content_desc_attribute and "Open navigation menu" in content_desc_attribute) or (content_desc_attribute and  "Открыть меню навигации" in content_desc_attribute):
                logger.info(f"[{thread_name}] [{self.avd_name}]: Убедились в том, что вы действительно авторизованы!")
                return True


    def ensure_is_in_telegram_app(self):
        thread_name = threading.current_thread().name

        try:
            logger.info(f"[{thread_name}] [{self.avd_name}]: Убедились, что приложение Telegram открыто.")
            if not self.navigate_to_saved_messages():
                return False
            else:
                logger.info(f"[{thread_name}] [{self.avd_name}]: Успешно перешли в \"Избранное\".")
                self.was_entered_saved_messages_page = True
            return True
        except Exception as e:
            logger.error(f"[{thread_name}] [{self.avd_name}]: Ошибка при попытке открыть Telegram: {e}")
            raise


    def navigate_to_saved_messages(self):
        thread_name = threading.current_thread().name

        try:
            if not self.check_if_not_authorized(thread_name=thread_name):
                return False

            navigation_menu_locator_ru = "//android.widget.ImageView[@content-desc='Открыть меню навигации']"
            navigation_menu_locator_en = "//android.widget.ImageView[@content-desc='Open navigation menu']"

            navigation_menu_el = Meh.wait_for_element_xpath(
                navigation_menu_locator_ru,
                navigation_menu_locator_en,
                driver=self.driver,
                timeout=30
            )

            navigation_menu_el.click()

            logger.info(f"[{thread_name}] [{self.avd_name}]: Кнопка меню навигации успешно нажата!")

            saved_messages_locator_ru = "(//android.widget.TextView[@text='Избранное'])[1]"
            saved_messages_locator_en = "(//android.widget.TextView[@text='Saved Messages'])[1]"
            saved_messages_el = Meh.wait_for_element_xpath(
                saved_messages_locator_ru,
                saved_messages_locator_en,
                driver=self.driver,
                timeout=30
            )

            saved_messages_el.click()

            logger.info(f"[{thread_name}] [{self.avd_name}]: Кнопка 'Избранное' успешно нажата!")
            return True
        except Exception as ex:
            logger.warning(f"[{thread_name}] [{self.avd_name}]: Произошла ошибка в процессе перехода в \"Избранное\": {ex}")
            self.ensure_is_in_telegram_app()
            return False


    def send_message_with_phone_number(self, phone_number):
        thread_name = threading.current_thread().name

        try:
            logger.info(f"[{thread_name}] [{self.avd_name}]: Пробуем проверить номер {phone_number}.")

            message_field_not_empty_locator = "//android.widget.EditText[string-length(@text) > 0]"
            message_field_empty_locator = "//android.widget.EditText[contains(@text, 'Message') or contains(@text, 'Сообщение')"
            message_field_el = Meh.wait_for_element_xpath(
                message_field_not_empty_locator,
                message_field_empty_locator,
                driver=self.driver,
                timeout=30,
                interval=3
            )


            if not "Сообщение" in message_field_el.get_attribute("text") or not "Message" in message_field_el.get_attribute("text"):
                hint = message_field_el.get_attribute("hint")
                if hint and "Message" in hint:
                    message_field_el.clear()
                    time.sleep(1)

            if "Сообщение" in message_field_el.get_attribute("text") or "Message" in message_field_el.get_attribute("text"):
                message_field_el.click()
                time.sleep(1)

                message_field_el.send_keys(phone_number)
                time.sleep(2)



            send_button_locator_ru = "//android.view.View[@content-desc='Отправить']"
            send_button_locator_en = "//android.view.View[@content-desc='Send']"

            send_button_el = Meh.wait_for_element_xpath(
                send_button_locator_ru,
                send_button_locator_en,
                driver=self.driver,
                timeout=30,
                interval=3
            )

            send_button_el.click()

            current_number_message_locator_1 = f"//android.view.ViewGroup[contains(@text, '{phone_number}')][last()]"
            current_number_message_locator_2 = f"//android.view.View[contains(@content-desc, '{phone_number}')][last()]"

            current_number_message_el = Meh.wait_for_element_xpath(
                current_number_message_locator_1,
                current_number_message_locator_2,
                driver=self.driver,
                timeout=30,
                interval=3
            )

            # Получение координат элемента
            rect = current_number_message_el.rect
            # logger.info(rect)
            center_x = rect['x'] + (rect['width'] // 2)
            center_y = rect['y'] + (rect['height'] // 2)

            shifted_x = int(center_x + center_x * 0.25)
            shifted_y = int(center_y + center_y * 0.05)

            logger.info(f"[{thread_name}] [{self.avd_name}]: Клик по центру элемента последнего сообщения: x={shifted_x}, y={shifted_y}") # Заменить shifted_y на center_y, если не заработает.


            # Выполнение клика по центру элемента
            self.actions.w3c_actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
            self.actions.w3c_actions.pointer_action.move_to_location(shifted_x, center_y)
            self.actions.w3c_actions.pointer_action.pointer_down()
            self.actions.w3c_actions.pointer_action.pointer_up()
            self.actions.perform()

            show_profile_btn_locator_ru = "//android.widget.TextView[contains(@text, 'Перейти в профиль')]"
            show_profile_btn_locator_en = "//android.widget.TextView[contains(@text, 'View Profile')]"
            profile_doesnt_exist_locator_ru = "//android.widget.TextView[contains(@text, 'Номер не зарегистрирован в Telegram')]"
            profile_doesnt_exist_locator_en = "//android.widget.TextView[contains(@text, 'This number is not on Telegram')]"
            delete_button_locator_ru ="//android.widget.TextView[@text='Delete']"
            delete_button_locator_en = "//android.widget.TextView[@text='Удалить']"

            element = Meh.wait_for_element_xpath(
                show_profile_btn_locator_ru,
                show_profile_btn_locator_en,
                profile_doesnt_exist_locator_ru,
                profile_doesnt_exist_locator_en,
                delete_button_locator_ru,
                delete_button_locator_en,
                driver=self.driver,
                timeout=30
            )


            if "Перейти в профиль" in element.get_attribute("text") or "View Profile" in element.get_attribute("text"):
                logger.info(f"[{thread_name}] [{self.avd_name}]: Номер {phone_number} зарегистрирован в Telegram!")
                return True
            elif "Номер не зарегистрирован в Telegram" in element.get_attribute("text") or "This number is not on Telegram" in element.get_attribute("text"):
                logger.info(f"[{thread_name}] [{self.avd_name}]: Номер {phone_number} не зарегистрирован в Telegram.")
                return False
            elif "Удалить" in element.get_attribute("text") or "Delete" in element.get_attribute("text"):
                logger.info(f"[{thread_name}] [{self.avd_name}]: Номер {phone_number} не удалось проверить...")
                return False

        except Exception as ex:
            self.ensure_is_in_telegram_app()
            logger.info(f"[{thread_name}] [{self.avd_name}]: Произошла ошибка в процессе проверки номера: {ex}")


    def install_or_update_telegram_apk(self, apk_version_manager: TelegramApkVersionManager, apk_path, emulator_port):
        """
        Устанавливает или обновляет Telegram APK на эмуляторе.
        Если версия установленного приложения устарела, выполняется обновление.
        """
        thread_name = threading.current_thread().name

        # Получаем версию из скачанного APK
        downloaded_version = apk_version_manager.get_app_version(apk_path)
        if not downloaded_version:
            logger.error(f"[{thread_name}] [{self.avd_name}] Не удалось определить версию APK. Пропуск установки.")
            raise

        logger.info(f"[{thread_name}] [{self.avd_name}] Версия APK для установки: {downloaded_version}")

        # Получаем текущую версию установленного приложения
        installed_version = apk_version_manager.get_installed_app_version(emulator_port)
        if installed_version:
            logger.info(f"[{thread_name}] [{self.avd_name}] Текущая версия Telegram на устройстве: {installed_version}")
        else:
            logger.warning(f"[{thread_name}] [{self.avd_name}] Telegram не установлен на устройстве. Установка новой версии...")

        # Сравнение версий
        if installed_version == downloaded_version:
            logger.info(f"[{thread_name}] [{self.avd_name}] Установленная версия актуальна. Установка не требуется.")
            return
        elif installed_version and installed_version < downloaded_version:
            logger.warning(f"[{thread_name}] [{self.avd_name}] Установлена устаревшая версия Telegram. Выполняется обновление...")
            try:
                # Обновление APK
                update_command = [
                    "adb", "-s", f"emulator-{emulator_port}", "install", "-r", apk_path
                ]
                result = subprocess.run(update_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if "Success" in result.stdout:
                    logger.info(f"[{thread_name}] [{self.avd_name}] Telegram успешно обновлён до версии {downloaded_version}.")
                else:
                    logger.error(f"[{thread_name}] [{self.avd_name}] Ошибка при обновлении Telegram: {result.stderr}")
            except Exception as e:
                logger.error(f"[{thread_name}] [{self.avd_name}] Ошибка при попытке обновить приложение: {e}")
        else:
            logger.warning(f"[{thread_name}] [{self.avd_name}] Telegram не установлен. Выполняется установка...")
            try:
                # Установка APK
                self.driver.install_app(apk_path)
                logger.info(f"[{thread_name}] [{self.avd_name}] Telegram успешно установлен.")
            except Exception as e:
                logger.error(f"[{thread_name}] [{self.avd_name}] Ошибка при установке Telegram: {e}")
