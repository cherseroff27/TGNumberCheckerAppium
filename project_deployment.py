import os
import subprocess
import shutil


# Шаг 1. Создание виртуального диска VHD
def create_vhd(vhd_name="sandbox_tg_automation"):
    # Путь к виртуальному диску
    vhd_path = f"C:\\{vhd_name}.vhdx"

    # Размер диска (например, 10GB)
    disk_size = "10GB"

    # Создаем виртуальный диск через PowerShell (с помощью diskpart)
    command = f"powershell New-VHD -Path {vhd_path} -SizeBytes {disk_size} -Dynamic"
    subprocess.run(command, shell=True, check=True)
    print(f"Виртуальный диск создан: {vhd_path}")

    return vhd_path


# Шаг 2. Инициализация и форматирование диска
def initialize_and_format_vhd(vhd_path):
    # Форматирование и монтирование виртуального диска через diskpart
    diskpart_script = f"""
    select vdisk file={vhd_path}
    attach vdisk
    create partition primary
    format fs=ntfs quick
    assign letter=Z
    """

    # Запускаем diskpart
    with open("script.txt", "w") as file:
        file.write(diskpart_script)

    subprocess.run("diskpart /s script.txt", shell=True, check=True)
    os.remove("script.txt")
    print("Диск отформатирован и присвоена буква Z")


# Шаг 3. Копирование файлов на виртуальный диск
def copy_files_to_vhd(vhd_letter="Z", script_path="path_to_script.exe"):
    # Путь к файлам на виртуальном диске
    vhd_script_dir = f"{vhd_letter}:\\Script"
    os.makedirs(vhd_script_dir, exist_ok=True)

    # Копирование исполняемого файла и папок
    shutil.copy(script_path, vhd_script_dir)
    print(f"Файлы скрипта скопированы в {vhd_script_dir}")

    # Создание дополнительных папок, если нужно
    os.makedirs(f"{vhd_script_dir}\\config", exist_ok=True)
    os.makedirs(f"{vhd_script_dir}\\logs", exist_ok=True)
    print("Необходимые папки созданы на виртуальном диске")


# Шаг 4. Формирование файла .wsb для Windows Sandbox
def create_wsb_file(vhd_name="sandbox_tg_automation", vhd_letter="Z", script_name="script.exe"):
    # Путь к исполняемому файлу скрипта
    script_path = f"{vhd_letter}:\\Script\\{script_name}"

    # Конфигурация для Windows Sandbox
    wsb_content = f"""
    <Configuration>
      <MappedFolders>
        <MappedFolder>
          <HostFolder>{vhd_name}.vhdx</HostFolder>
          <ReadOnly>false</ReadOnly>
        </MappedFolder>
      </MappedFolders>
      <LogonCommand>
        <Command>{script_path}</Command>
      </LogonCommand>
      <Networking>Enable</Networking>
      <AudioInput>Enable</AudioInput>
      <VideoInput>Enable</VideoInput>
    </Configuration>
    """

    # Сохранение конфигурации в файл .wsb
    wsb_path = f"{vhd_name}.wsb"
    with open(wsb_path, "w") as wsb_file:
        wsb_file.write(wsb_content)

    print(f"Файл конфигурации .wsb создан: {wsb_path}")

    return wsb_path


# Шаг 5. Запуск процесса
def main():
    # Путь к исполняемому файлу
    script_path = "C:\\path_to_script.exe"  # Укажите свой путь к файлу

    # Шаг 1. Создаем виртуальный диск
    vhd_name = "sandbox_tg_automation"
    vhd_path = create_vhd(vhd_name)

    # Шаг 2. Инициализация и форматирование
    initialize_and_format_vhd(vhd_path)

    # Шаг 3. Копируем файлы на виртуальный диск
    copy_files_to_vhd(script_path=script_path)

    # Шаг 4. Создание и сохранение конфигурационного файла .wsb
    wsb_file_path = create_wsb_file(vhd_name=vhd_name, vhd_letter="Z", script_name="script.exe")

    # Опционально: Запуск Windows Sandbox с созданным .wsb файлом
    subprocess.run(f"start {wsb_file_path}", shell=True)


if __name__ == "__main__":
    main()
