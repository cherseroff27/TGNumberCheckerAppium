import random
import time
from typing import Optional, Tuple

from selenium.common import TimeoutException, StaleElementReferenceException, ElementNotInteractableException
from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class MobileElementsHandler:
    def __init__(self):
        pass

    @staticmethod
    def click_element(driver: WebDriver, element: WebElement):
        """
        Кликает по элементу, выполняя прокрутку к нему, если это необходимо.
        :param driver: WebDriver Appium.
        :param element: Элемент для взаимодействия.
        """
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()
        except Exception as e:
            print(f"Ошибка при клике по элементу: {e}")

    @staticmethod
    def wait_for_element_xpath(
            *locators: str,
            driver: WebDriver,
            timeout: int = 30,
            interval: int = 1,
    ) -> Optional[WebElement]:
        """
        Ожидает появления элемента по XPath.
        :param locators: Локаторы элементов в формате XPath.
        :param driver: WebDriver Appium.
        :param timeout: Таймаут ожидания.
        :param interval: Интервал между попытками.
        :return: Найденный элемент или None.
        """
        locator_tuples = [(By.XPATH, locator) for locator in locators]
        try:
            return MobileElementsHandler.wait_for_element_tuple(
                *locator_tuples, driver=driver, timeout=timeout, interval=interval
            )
        except TimeoutException as e:
            print(f"Элемент с локаторами {locator_tuples} не найден за {timeout} секунд. Ошибка: {e}")
            return None

    @staticmethod
    def wait_for_element_tuple(
            *locators: Tuple[str, str], driver: WebDriver, timeout: int = 30, interval: int = 1
    ) -> Optional[WebElement]:
        """
        Ожидает появления элемента по нескольким локаторам.
        :param locators: Кортежи локаторов (например, (By.XPATH, "//xpath")).
        :param driver: WebDriver Appium.
        :param timeout: Таймаут ожидания.
        :param interval: Интервал между попытками.
        :return: Найденный элемент или None.
        """
        end_time = time.time() + timeout

        while time.time() < end_time:
            try:
                element = WebDriverWait(driver, interval).until(
                    EC.any_of(
                        *[EC.presence_of_element_located(locator) for locator in locators]
                    )
                )
                if element:
                    return element
            except StaleElementReferenceException:
                print("Элемент обновился в DOM. Повторяем попытку...")
            except TimeoutException:
                print("Элемент не найден в течение текущей попытки.")
            except Exception as e:
                print(f"Произошла ошибка при поиске элемента: {e}")
            time.sleep(0.5)
        raise TimeoutException(f"Не удалось найти элементы с локаторами: {locators}")

    @staticmethod
    def ensure_element_is_interactable(driver: WebDriver, locator: Tuple[str, str], timeout: int = 10) -> bool:
        """
        Проверяет, что элемент доступен для взаимодействия.
        :param driver: WebDriver Appium.
        :param locator: Локатор элемента (например, (By.XPATH, "//xpath")).
        :param timeout: Таймаут ожидания.
        :return: True, если элемент доступен, иначе False.
        """
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(locator)
            )

            if not element.is_displayed():
                print("Элемент не видим.")
                return False

            if not element.is_enabled():
                print("Элемент не активен.")
                return False

            return True
        except TimeoutException:
            print("Элемент недоступен для взаимодействия в течение заданного времени.")
            return False

    @staticmethod
    def slow_typing(element: WebElement, text: str, use_clipboard: bool = False):
        """
        Вводит текст с задержкой между символами.
        :param element: Элемент для ввода текста.
        :param text: Вводимый текст.
        :param use_clipboard: Вставить текст целиком, если True.
        """
        if use_clipboard:
            element.send_keys(text)
            return

        for char in text:
            delay = random.uniform(0.05, 0.2)
            try:
                element.send_keys(char)
            except ElementNotInteractableException:
                print("Элемент недоступен для ввода.")
                raise
            time.sleep(delay)
