import re
import asyncio
from pyrogram import Client
from pyrogram.errors import PhoneNumberInvalid, FloodWait
from openpyxl import Workbook
from typing import Optional, List, Dict
import os
import logging
from colorama import Fore, Style

# ===========================
# Настройки
# ===========================
API_ID = 28511294  # Замените на ваш API ID
API_HASH = "db3f4daaca54939ebfbcade4d2fdb444"  # Замените на ваш API Hash
PHONE_NUMBER = "+79902583256"  # Номер телефона пользователя
MAX_THREADS = 10  # Максимальное количество потоков
INPUT_NUMBERS = [
    "88005553535", "74951234567", "73351234567", "+1 234 567 890", "8 (800) 555-35-35", "invalid_number",
    "89991234567", "89261234567", "89371234567", "89871234567", "89994567890",
    "84951112233", "84957895432", "88001231234", "88002503677", "84951234567",
    "89991230001", "89991230002", "89991230003", "89991230004", "89991230005",
    "89991230006", "89991230007", "89991230008", "89991230009", "89991230010",
    "+79871234567", "+79161234567", "+79621234567", "+79501234567", "+79991234567"
]  # Пример номеров (сокращен для читабельности)
SESSION_DIR = os.path.join(os.getcwd(), "sessions")
os.makedirs(SESSION_DIR, exist_ok=True)
SESSION_NAME = os.path.join(SESSION_DIR, "user_session")

# Логирование с цветами
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def log_with_color(level: str, message: str):
    color_map = {
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
    }
    print(color_map.get(level, "") + message + Style.RESET_ALL)


# ===========================
# Функции
# ===========================

def format_number(phone: str) -> Optional[str]:
    """
    Приведение номера к формату +7xxxxxxxxxx.
    Если номер не валиден, возвращается None.
    """
    log_with_color("INFO", f"Форматируем номер: {phone}")
    phone = re.sub(r"\D", "", phone)
    if phone.startswith("8"):
        phone = "+7" + phone[1:]
    elif not phone.startswith("+7"):
        log_with_color("WARNING", f"Номер не валиден: {phone}")
        return None
    if len(phone) == 12:
        log_with_color("INFO", f"Номер успешно отформатирован: {phone}")
        return phone
    log_with_color("WARNING", f"Номер некорректной длины: {phone}")
    return None


async def check_telegram_registration(app: Client, phone: str) -> bool:
    """
    Проверка, зарегистрирован ли номер в Telegram.
    """
    log_with_color("INFO", f"Проверяем регистрацию номера: {phone}")
    try:
        await app.send_code(phone)
        log_with_color("INFO", f"Номер зарегистрирован в Telegram: {phone}")
        return True
    except PhoneNumberInvalid:
        log_with_color("WARNING", f"Номер не зарегистрирован: {phone}")
        return False
    except FloodWait as e:
        log_with_color("WARNING", f"FloodWait: Ожидание {e.value} секунд.")
        await asyncio.sleep(e.value)
        return await check_telegram_registration(app, phone)
    except Exception as e:
        log_with_color("ERROR", f"Ошибка при проверке номера {phone}: {e}")
        return False


async def process_number(app: Client, phone: str) -> Dict:
    """
    Обработка одного номера: форматирование и проверка в Telegram.
    """
    log_with_color("INFO", f"Обрабатываем номер: {phone}")
    formatted_phone = format_number(phone)
    if not formatted_phone:
        log_with_color("WARNING", f"Номер не отформатирован: {phone}")
        return {"phone": phone, "formatted": None, "registered": None}

    try:
        is_registered = await check_telegram_registration(app, formatted_phone)
        return {"phone": phone, "formatted": formatted_phone, "registered": is_registered}
    except Exception as e:
        log_with_color("ERROR", f"Ошибка обработки номера {phone}: {e}")
        return {"phone": phone, "formatted": formatted_phone, "registered": None}


def save_results_to_excel(registered: List[Dict], unregistered: List[Dict]):
    """
    Сохранение результатов в Excel.
    """
    wb = Workbook()
    ws_registered = wb.active
    ws_registered.title = "Registered Numbers"
    ws_unregistered = wb.create_sheet(title="Unregistered Numbers")

    ws_registered.append(["Original Phone", "Formatted Phone"])
    ws_unregistered.append(["Original Phone", "Formatted Phone"])

    for item in registered:
        ws_registered.append([item["phone"], item["formatted"]])

    for item in unregistered:
        ws_unregistered.append([item["phone"], item["formatted"]])

    file_path = os.path.join(SESSION_DIR, "telegram_numbers.xlsx")
    try:
        wb.save(file_path)
        log_with_color("INFO", f"Результаты сохранены в {file_path}")
    except PermissionError as e:
        log_with_color("ERROR", f"Не удалось сохранить файл: {e}")


# ===========================
# Основной процесс
# ===========================

async def main():
    registered, unregistered = [], []

    async with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, phone_number=PHONE_NUMBER) as app:
        tasks = [process_number(app, phone) for phone in INPUT_NUMBERS]
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result["formatted"]:
                if result["registered"]:
                    registered.append(result)
                else:
                    unregistered.append(result)

    save_results_to_excel(registered, unregistered)


if __name__ == "__main__":
    asyncio.run(main())
