import os
import sys
import subprocess


def find_tcl_tk_paths():
    """
    Определяет пути к библиотекам Tcl и Tk из глобальной установки Python.
    """
    # Проверяем глобальную установку Python
    global_python = sys.base_prefix  # Базовый путь Python, не зависящий от виртуального окружения
    tcl_path = os.path.join(global_python, 'tcl', 'tcl8.6')
    tk_path = os.path.join(global_python, 'tcl', 'tk8.6')

    if not os.path.exists(tcl_path) or not os.path.exists(tk_path):
        raise FileNotFoundError("Не найдены директории Tcl или Tk в глобальной установке Python.")

    return tcl_path, tk_path


def build_exe():
    """
    Сборка exe с помощью PyInstaller, добавляя пути к Tcl/Tk из глобальной установки и иконку приложения.
    """
    tcl_path, tk_path = find_tcl_tk_paths()

    icon_path = "icon.ico"
    if not os.path.exists(icon_path):
        raise FileNotFoundError(f"Файл иконки {icon_path} не найден.")

    pyinstaller_command = [
        "pyinstaller",
        "--clean",
        "--onefile",
        "--console",
        "--name", "TGNumberCheckerAutomation",
        "--add-data", f"{tcl_path};lib\\tcl8.6",
        "--add-data", f"{tk_path};lib\\tk8.6",
        "--icon", icon_path,
        "TGAppiumEmulatorAutomationApp.py",
    ]

    # Запуск команды PyInstaller
    subprocess.run(pyinstaller_command, check=True)


if __name__ == "__main__":
    try:
        build_exe()
        print("Сборка завершена успешно!")
    except Exception as e:
        print(f"Ошибка сборки: {e}")
