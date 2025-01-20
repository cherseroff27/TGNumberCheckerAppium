import ctypes
from logger_config import Logger
logger = Logger.get_logger(__name__)

def notify_environment_change():
    """Отправляет сообщение WM_SETTINGCHANGE для немедленного применения изменений переменных среды."""
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x1A

    result = ctypes.windll.user32.SendMessageTimeoutA(
        HWND_BROADCAST,
        WM_SETTINGCHANGE,
        0,
        ctypes.cast(ctypes.c_char_p(b"Environment"), ctypes.POINTER(ctypes.c_char)),
        0,
        5000,  # Таймаут 5 секунд
        None
    )
    if result == 0:
        logger.warning(
            "Не удалось отправить сообщение WM_SETTINGCHANGE. Переменные среды могут примениться с задержкой.")
    else:
        logger.info("Изменения переменных среды применены немедленно.")



notify_environment_change()