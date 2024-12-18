import time

from manual_script_control import ManualScriptControl
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver import ActionChains
from MobileElementsHandler import MobileElementsHandler as Meh


class TelegramMobileAppAutomation:
    def __init__(self, driver, avd_name, emulator_auth_config_manager, excel_processor):
        self.driver = driver
        self.emulator_auth_config_manager = emulator_auth_config_manager
        self.excel_processor = excel_processor
        self.avd_name = avd_name
        self.actions = ActionChains(driver)


    def ensure_is_in_telegram_app(self, profile_name):
        pass


    def ensure_is_on_main_screen(self,):
        pass


    def ensure_is_authorized_in_telegram(self):
        pass


    def authorize_if_needed(self):
        try:
            if not self.emulator_auth_config_manager.is_authorized(self.avd_name):
                ManualScriptControl.wait_for_user_input(f"[{self.avd_name}]: Авторизуйтесь в Telegram Web и нажмите Enter для продолжения.")
        except Exception as e:
            print(f"[{self.avd_name}]: Ошибка авторизации для эмулятора: {e}")


    def send_message_with_phone_number(self, phone_number):
        # Запуск настроек для теста
        self.driver.activate_app("com.android.settings")

        ManualScriptControl.wait_for_user_input(f"[{self.avd_name}]: Загрузился в эмулятор")
        try:
            navigation_menu_locator = "//android.widget.ImageView[@content-desc='Открыть меню навигации']"
            navigation_menu_el = Meh.wait_for_element_xpath(
                navigation_menu_locator, driver=self.driver, timeout=15)

            navigation_menu_el.click()

            print(f"[{self.avd_name}]: Кнопка меню навигации успешно нажата!")



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

