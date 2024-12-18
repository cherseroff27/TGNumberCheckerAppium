import sys
import time

from manual_script_control import ManualScriptControl
from browser_manager import BrowserManager
from web_elements_handler import WebElementsHandler as Weh


class TelegramWebAutomation:
    def __init__(self, profile_manager, excel_processor, browser_profiles_dir):
        self.driver = None
        self.profile_manager = profile_manager
        self.excel_processor = excel_processor
        self.browser_profiles_dir = browser_profiles_dir
        self.web_telegram_link = "https://web.telegram.org/a"


    def setup_driver(self, profile_name):
        # Получаем уникальный путь для кэша на основе идентификатора потока
        browser_manager = BrowserManager()

        self.driver = browser_manager.initialize_webdriver(
            browser_profiles_dir=self.browser_profiles_dir,
            use_profile_folder=True,
            profile_name=profile_name,
        )

        if self.driver is None:
            print("driver == None")
            sys.exit()
        else:
            print(f"driver successfully initialized: {self.driver}")


    def authorize_if_needed(self, profile_name):
        try:
            if not self.profile_manager.is_authorized(profile_name):
                self.driver.get(self.web_telegram_link)
                ManualScriptControl.wait_for_user_input("Авторизуйтесь в Telegram Web и нажмите Enter для продолжения.")
                if self.ensure_is_authorized_in_telegram():
                    self.profile_manager.mark_as_authorized(profile_name)
                    print(f"Пометил профиль браузера в конфиге как \"Авторизованный в Telegram\"")
        except Exception as e:
            print(f"Ошибка авторизации для профиля {profile_name}: {e}")


    def ensure_is_authorized_in_telegram(self,):
        search_field_locator = "#telegram-search-input"
        try:
            if Weh.wait_for_element_css(search_field_locator, driver=self.driver, timeout=30) is not None:
                print("Успешно вошел в телеграм аккаунт.")
                return True
            else:
                print("Ошибка при входе в телеграм аккаунт.")
                return
        except Exception as ex:
            print(f"Не ужалось убедится в наличии элемента кнопки \"Поиска\": {ex}")


    def add_contact(self, phone_number):
        try:
            self.driver.get(self.web_telegram_link)
            time.sleep(2)

            sidebar_button_selector = "#LeftMainHeader div.DropdownMenu.main-menu"
            sidebar_button_el = Weh.wait_for_element_css(sidebar_button_selector, driver=self.driver, timeout=30)
            if sidebar_button_el is not None:
                sidebar_button_el.click()

            contacts_button_locator = "(//div[contains(@class, 'MenuItem')]//i)[2]"
            contacts_button_el = Weh.wait_for_element_xpath(contacts_button_locator, driver=self.driver, timeout=30)
            if contacts_button_el is not None:
                contacts_button_el.click()

            add_contact_button_locator = "//button[@type='button']//i[@class='icon icon-add-user-filled']"
            add_contact_button_el = Weh.wait_for_element_xpath(add_contact_button_locator, driver=self.driver, timeout=30)
            if add_contact_button_el is not None:
                add_contact_button_el.click()

            phone_number_field_locator = "//input[@inputmode='tel']"
            add_contact_button_el = Weh.wait_for_element_xpath(phone_number_field_locator, driver=self.driver, timeout=30)
            if add_contact_button_el is not None:
                add_contact_button_el.send_keys(phone_number)

            name_field_locator = "//input[not(@inputmode='tel') and (contains(@aria-label, 'First name') or contains(@aria-label, 'Имя'))]"
            name_field_el = Weh.wait_for_element_xpath(name_field_locator, driver=self.driver, timeout=30)
            if name_field_el is not None:
                name_field_el.send_keys(phone_number)

            add_button_locator = "//button[contains(@class, 'confirm-dialog-button')][1]"
            add_button_el = Weh.wait_for_element_xpath(add_button_locator, driver=self.driver, timeout=30)
            if add_button_el is not None:
                add_button_el.click()
            try:
                failure_notification_locator = "//div[contains(@class, 'Notification-container')]//div[contains(@class, 'Notification')]//div[contains(@class, 'content')]"
                editable_message_locator = "//div[@id='editable-message-text']"
                found_element = Weh.wait_for_element_xpath(failure_notification_locator, editable_message_locator, driver=self.driver, timeout=30)
                
                if found_element is not None:
                    if "content" in found_element.get_attribute("class"):
                        print("Найден элемент 'Notification'. Номер не зарегистрирован в Telegram.")
                        time.sleep(10)
                        return False
                    elif "editable-message-text" in found_element.get_attribute("id"):
                        print("Найден элемент 'editable-message-text'. Номер зарегистрирован в Telegram.")
                        time.sleep(10)
                        return True
            except Exception as e:
                print(f"Ошибка при попытке сравнения атрибутов контакта: {e}")
                return False
        except Exception as e:
            print(f"Ошибка при добавлении контакта: {e}")
            return False


