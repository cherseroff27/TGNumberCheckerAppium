import subprocess

def list_available_packages():
    try:
        # Запускаем команду sdkmanager --list
        process = subprocess.Popen(
            ["sdkmanager", "--list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        available_packages = []
        capture = False

        # Читаем вывод команды построчно
        for line in process.stdout:
            # Если строка начинается с "Available packages:", начинаем захват
            if "Available packages:" in line:
                capture = True
                continue

            # Если строка начинается с "Installed packages:", прекращаем захват
            if "Installed packages:" in line:
                break

            # Сохраняем строку, если она относится к доступным пакетам
            if capture:
                available_packages.append(line.strip())

        # Возвращаем отфильтрованный результат
        return available_packages

    except Exception as e:
        print(f"Ошибка: {e}")
        return []

# Используем функцию
if __name__ == "__main__":
    packages = list_available_packages()
    print("Available packages:")
    print("\n".join(packages))