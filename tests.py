import os
import subprocess


def configure_environment():
    # Путь к SDK и Java в проекте
    project_dir = os.getcwd()
    sdk_path = os.path.join(project_dir, "android_sdk")
    java_path = os.path.join(project_dir, "java\\jdk-23")  # Убираем \\bin

    # Установка переменных окружения
    os.environ["ANDROID_HOME"] = sdk_path
    os.environ["JAVA_HOME"] = java_path
    os.environ["Path"] = ";".join([  # Обновляем Path
        os.environ.get("Path", ""),
        os.path.join(sdk_path, "platform-tools"),                  # ADB
        os.path.join(sdk_path, "cmdline-tools", "latest", "bin"),  # AVDManager
        os.path.join(sdk_path, "emulator"),                       # Emulator
        os.path.join(sdk_path, "build-tools", "35.0.0"),          # Build Tools
    ])


def check_tool_availability(tool):
    try:
        result = subprocess.run([tool, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{tool} доступен: {result.stdout.strip()}")
        else:
            print(f"{tool} недоступен.")
    except FileNotFoundError:
        print(f"{tool} не найден.")


if __name__ == "__main__":
    configure_environment()

    # Проверяем доступность ключевых инструментов
    print("Проверяем инструменты:")
    check_tool_availability("adb")
    check_tool_availability("java")

    # Проверка наличия AVD
    command = "avdmanager list avd"
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    print(result.stdout.strip())

    # Проверка наличия эмулятора
    result = subprocess.run("emulator", capture_output=True, text=True)
    if result.returncode == 0:
        print(f"emulator доступен: {result.stdout.strip()}")
    else:
        print(f"emulator недоступен.")
