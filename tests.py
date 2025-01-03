import sys


def is_virtualization_enabled():
    """
    Проверяет, включена ли виртуализация на уровне процессора (Intel VT-x/AMD-V).
    """
    try:
        # Используем ctypes для вызова CPUID на Windows
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            system_info = ctypes.create_string_buffer(64)
            kernel32.GetSystemInfo(ctypes.byref(system_info))
            return "Virtualization" in system_info.raw.decode(errors="ignore")
        else:
            # Для других ОС можно реализовать дополнительные проверки
            return True
    except Exception as e:
        print(f"Ошибка проверки виртуализации: {e}")
        return False


if is_virtualization_enabled():
    print(123)