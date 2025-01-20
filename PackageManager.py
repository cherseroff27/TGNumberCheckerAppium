import os
import shutil
import subprocess
import zipfile
import requests
from tqdm import tqdm

from logger_config import Logger
logger = Logger.get_logger(__name__)


class PackageManager:
    def __init__(self):
        pass


    @staticmethod
    def download_tool(filename, url, target_dir):
        """Загружает файл с отображением прогресса."""
        os.makedirs(target_dir, exist_ok=True)  # Создаем директорию, если её нет
        archive_path = os.path.join(target_dir, f"{filename}_temp.zip")

        # Если файл уже существует, пропускаем загрузку
        if os.path.exists(archive_path):
            logger.info(f"Файл {filename} уже существует в кэше: {archive_path}. Пропускаем загрузку.")
            return archive_path

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))  # Получаем общий размер файла
            chunk_size = 8192  # Размер блока данных

            with open(archive_path, "wb") as file, tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"Downloading {filename}",
                    colour="green"
            ) as progress_bar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    file.write(chunk)
                    progress_bar.update(len(chunk))  # Обновляем прогресс-бар

            return archive_path
        else:
            raise Exception(f"Не удалось скачать файл {filename} с {url}. Status code: {response.status_code}")


    @staticmethod
    def unpack_tool(archive_path, target_dir, extract_top_folder=False):
        """
        Распаковывает архив в нужную директорию.
        Если в архиве верхнего уровня находится одна папка, позволяет извлечь только её содержимое
        или саму папку вместе с её содержимым в зависимости от значения аргумента extract_top_folder.

        :param archive_path: Путь к архиву.
        :param target_dir: Директория, куда распаковывать.
        :param extract_top_folder: Если True, извлекается верхняя папка вместе с её содержимым.
                                   Если False, извлекается только содержимое верхней папки.
        """
        logger.info(f"Распаковываем архив {archive_path} в {target_dir}...")

        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            # Получаем список всех файлов и папок в архиве
            all_files = zip_ref.namelist()

            # Проверяем верхний уровень архива
            top_level_items = {os.path.normpath(f).split(os.sep)[0] for f in all_files}

            if len(top_level_items) == 1:
                # В архиве одна верхняя папка
                top_folder = top_level_items.pop()
                if extract_top_folder:
                    # Извлекаем верхнюю папку вместе с её содержимым
                    logger.info(f"Извлекаем верхнюю папку '{top_folder}' вместе с её содержимым.")
                    zip_ref.extractall(target_dir)
                else:
                    # Извлекаем только содержимое верхней папки
                    logger.info(f"Извлекаем только содержимое верхней папки '{top_folder}'.")
                    for file in all_files:
                        relative_path = os.path.relpath(file, start=top_folder)
                        if relative_path != ".":
                            target_path = os.path.join(target_dir, relative_path)
                            if not file.endswith('/'):  # Пропускаем директории, т.к. они создаются автоматически
                                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                                with zip_ref.open(file) as source_file:
                                    with open(target_path, "wb") as target_file:
                                        shutil.copyfileobj(source_file, target_file)
            else:
                # В архиве несколько элементов на верхнем уровне — извлекаем всё
                logger.info("В архиве нет единственной папки верхнего уровня. Извлекаем все содержимое.")
                zip_ref.extractall(target_dir)


    @staticmethod
    def fetch_package_version(package_name):
        """Проверяет, установлен ли компонент в системных переменных."""
        try:
            env = os.environ.copy()

            result = subprocess.run(
                [package_name, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
            )
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)

            if result.returncode != 0:
                raise RuntimeError(f"Ошибка выполнения команды: {result.stderr.strip()}")

            logger.info(f"{package_name} уже установлен.\nВерсия: {result.stdout.strip()}")
            return True
        except FileNotFoundError:
            logger.info(f"{package_name} не найден / еще не установлен.")
            return False


    @staticmethod
    def check_tool_availability(tool):
        result = subprocess.run(
            ["where", tool],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print(f"Результат проверки {tool}:")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)


    @staticmethod
    def is_package_installed(command, package_name):
        """ Проверяет, установлен ли компонент (ищет его в списке установленных). """
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
        )
        if package_name not in result.stdout:
            logger.info(f"Компонент [{package_name}] не установлен.")
            return False

        logger.info(f"Компонент [{package_name}] уже установлен.")
        return True


    @staticmethod
    def reset_and_prepare_dir(directory):
        if os.path.exists(directory):
            logger.info(f"Удаляю директорию компонента и настраиваю заново: {directory}...")
            shutil.rmtree(directory)


    @staticmethod
    def clear_tools_files_cache(temp_files_dir):
        """Удаляет все временные файлы из директории TEMP_FILES и выводит их названия в лог."""
        if os.path.exists(temp_files_dir):
            logger.info(f"Начинаем удаление закэшированных файлов из {temp_files_dir}...")

            # Получаем список всех файлов в директории
            for filename in os.listdir(temp_files_dir):
                file_path = os.path.join(temp_files_dir, filename)

                # Проверяем, что это файл (а не директория)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)  # Удаляем файл
                        logger.info(f"Удален файл: {filename}")  # Логируем удаление
                    except Exception as e:
                        logger.error(f"Ошибка при удалении файла {filename}: {e}")

            # После удаления всех файлов можем очистить директорию
            # если нужно восстановить структуру директории
            os.makedirs(temp_files_dir, exist_ok=True)

            logger.info("Закэшированные файлы успешно удалены.")
        else:
            logger.warning(f"Директория {temp_files_dir} отсутствует. Нечего удалять.")