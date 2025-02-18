import json
import os
import threading
from threading import Thread

import tkinter as tk
import tkinter.font as tk_font
from tkinter import filedialog, ttk, messagebox

from LocalVariablesManager import LocalVariablesManager

from logger_config import Logger
logger = Logger.get_logger(__name__)


class TelegramCheckerUI:
    def __init__(self, root, logic, app):
        self.app = app
        self.root = root
        self.logic = logic
        self.root.title("Telegram Number Checker")
        self.root.geometry("1200x900")
        self.loading_indicator = LoadingIndicator(self.root)

        self.header_font = tk_font.Font(family="Helvetica", size=11, weight="bold")
        self.custom_font = tk_font.Font(family="Calibri", size=10, weight="normal")

        self.saved_config = self.logic.load_threads_config()
        self.num_threads = tk.IntVar(value=self.saved_config.get("num_threads", 1))

        self.ram_size = tk.IntVar(value=logic.get_avd_property("ram_size"))
        self.disk_size = tk.IntVar(value=logic.get_avd_property("disk_size"))
        self.avd_ready_timeout = tk.IntVar(value=logic.get_avd_property("emulator_ready_timeout"))

        # Интерфейсные переменные
        latest_excel_file = logic.get_latest_excel_file()
        export_excel_file = logic.get_export_table_path(latest_excel_file)

        self.source_excel_file_path = tk.StringVar(value=latest_excel_file)
        self.export_table_path = tk.StringVar(value=export_excel_file)

        # Таблицы
        self.excel_frame = ttk.Frame(self.root)
        self.export_frame = ttk.Frame(self.root)
        self.excel_treeview = ttk.Treeview(columns=[], show="headings", height=5)

        self.start_button = None
        self.close_program_button = None
        self.exit_button = None

        # Создаем виджеты
        self.create_widgets()
        # Автозагрузка таблиц и профилей
        self.refresh_excel_table()

        self.widget_states = {}

        self.run_task_in_thread(
            task=self.logic.setup_all_tools,
            should_exit=False
        )


    def create_widgets(self):
        # Контейнер для первого ряда четырех кнопок
        top_buttons_frame = tk.Frame(self.root)
        top_buttons_frame.pack(fill="x", pady=5)

        # Центрирование кнопок в контейнере первого ряда кнопок
        first_level_top_buttons_inner_frame = tk.Frame(top_buttons_frame)
        first_level_top_buttons_inner_frame.pack(anchor="center")

        # Добавляем кнопки в контейнер
        tk.Label(first_level_top_buttons_inner_frame, text="Взаимодействие с эмуляторами и их конфигом (AVD):", font=self.header_font).pack(pady=5)
        tk.Button(first_level_top_buttons_inner_frame, text="Информация о\nсозданных AVD", font=self.custom_font, justify="center", command=self.show_config).pack(side="left", padx=5)
        tk.Button(first_level_top_buttons_inner_frame, text="Удалить конфиг\n(Информация об AVD)", font=self.custom_font, justify="center", command=self.delete_config).pack(side="left", padx=5)
        tk.Button(first_level_top_buttons_inner_frame, text="Сбросить флаг авторизации\nу всех AVD в конфиге", font=self.custom_font, justify="center", command=self.reset_all_authorizations).pack(side="left", padx=5)
        tk.Button(first_level_top_buttons_inner_frame, text="Посмотреть список\nсозданных AVD", font=self.custom_font, justify="center", command=self.show_existing_avds_list).pack(side="left", padx=5)
        tk.Button(first_level_top_buttons_inner_frame, text="Удалить все AVD\n(Созданные AVD)", font=self.custom_font, justify="center", command=self.delete_all_avds).pack(side="left", padx=5)
        tk.Button(first_level_top_buttons_inner_frame, text="Перезапустить\nabv-server", font=self.custom_font, justify="center", command=self.restart_adb_server).pack(side="left", padx=5)

        # Центрирование кнопок в контейнере второго ряда кнопок
        second_level_top_buttons_inner_frame = tk.Frame(top_buttons_frame)
        second_level_top_buttons_inner_frame.pack(anchor="center")

        tk.Label(second_level_top_buttons_inner_frame, text="Установка/удаление инструментов SDK/JDK их системных переменных и конфига", font=self.header_font).pack(pady=5)
        tk.Button(second_level_top_buttons_inner_frame, text="Установить SDK/JDK", font=self.custom_font, justify="center", command=self.download_and_setup_java_sdk_and_android_sdk_tools).pack(side="left", padx=5)
        tk.Button(second_level_top_buttons_inner_frame, text="Установить\nAppium, UIAutomator2", font=self.custom_font, justify="center", command=self.setup_appium_and_uiautomator2).pack(side="left", padx=5)
        # tk.Button(second_level_top_buttons_inner_frame, text="Скачать, установить\nNODE JS, добавить в\nпеременные среды", font=self.custom_font, justify="center", command=self.download_and_setup_node_js).pack(side="left", padx=5)
        # tk.Button(second_level_top_buttons_inner_frame, text="Проверить\nустановлен ли\nNODE JS", font=self.custom_font, justify="center", command=self.check_if_is_node_installed).pack(side="left", padx=5)
        tk.Button(second_level_top_buttons_inner_frame, text="Вывести в лог cписок\nлокальных переменных среды", font=self.custom_font, justify="center", command=self.get_all_local_environ_variables).pack(side="left", padx=5)
        tk.Button(second_level_top_buttons_inner_frame, text="Очистить папку TEMP_FILES\n(кэш файлов cmdline-tools и java jdk)",font=self.custom_font, justify="center", command=self.clear_tools_files_cache).pack(side="left", padx=5)

        # Файл Excel
        tk.Label(self.root, text="Файл таблицы Excel:", font=self.header_font).pack(pady=1)

        # Кнопка обновления содержимого Excel-файла
        tk.Button(self.excel_frame, text="Обновить\nтаблицу", font=self.custom_font, command=self.refresh_excel_table).pack(side="left", padx=3)
        tk.Entry(self.excel_frame, textvariable=self.source_excel_file_path, font=self.custom_font, width=50).pack(side="left", fill="x", expand=True, padx=5)
        # Кнопка выбрать файл
        tk.Button(self.excel_frame, text="Выбрать\nфайл", font=self.custom_font, command=self.browse_excel_file).pack(side="left", padx=5)
        # Кнопка открывающая выбранный файл таблицы в проводнике
        tk.Button(self.excel_frame, text="Открыть\nв проводнике", font=self.custom_font, command=lambda: self.open_in_explorer(self.source_excel_file_path)).pack(side="left", padx=5)
        self.excel_frame.pack(fill="x", padx=10, pady=5)

        # Поле для итогового файла
        tk.Label(self.root, text="Итоговый файл таблицы Excel:", font=self.header_font).pack(pady=1)
        tk.Entry(self.export_frame, textvariable=self.export_table_path, font=self.custom_font, width=50).pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(self.export_frame, text="Открыть\nв проводнике", font=self.custom_font, command=lambda: self.open_in_explorer(self.export_table_path)).pack(side="left", padx=5)
        self.export_frame.pack(fill="x", padx=10, pady=5)

        # Содержимое таблицы Excel
        tk.Label(self.root, text="Содержимое таблицы Excel:", font=self.header_font).pack(pady=1)
        self.excel_treeview.pack(fill="both", expand=True, padx=10, pady=5)

        # Контейнер для задания количества потоков, параметров AVD и кнопок управления
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill="x", pady=5)

        # Центрирование всего блока control_frame
        control_inner_frame = tk.Frame(control_frame)
        control_inner_frame.pack(anchor="center")

        # Подконтейнер для ввода параметров AVD
        avd_settings_frame = tk.Frame(control_inner_frame)
        avd_settings_frame.pack(side="left", padx=10)

        # Функция для создания поля ввода с подписью
        def create_labeled_entry(parent, label_text, variable):
            """Создает поле ввода с подписью над этим полем."""
            frame = tk.Frame(parent)
            frame.pack(side="left", padx=5)
            tk.Label(frame, text=label_text, font=tk_font.Font(family="Calibri", size=11, weight="bold")).pack()
            ttk.Entry(frame, textvariable=variable, width=8).pack()
            return frame

        # Поле для ввода количеств потоков и для ввода параметров AVD
        create_labeled_entry(avd_settings_frame, "Количество\nпотоков:", self.num_threads)

        # Кнопка сохранения параметров AVD в конфиг
        tk.Button(avd_settings_frame, text="Сохранить\nкол-во потоков\nпо умолчанию", command=self.save_default_threads_amount).pack(side="left", padx=5)

        create_labeled_entry(avd_settings_frame, "Кол-во ОЗУ\nна AVD (МБ):", self.ram_size)
        create_labeled_entry(avd_settings_frame, "Тайм-аут\nготовности AVD (сек.):", self.avd_ready_timeout)
        create_labeled_entry(avd_settings_frame, "Постоянная\nпамять (МБ):", self.disk_size)

        # Кнопка сохранения параметров AVD в конфиг
        tk.Button(avd_settings_frame, text="Сохранить\nпараметры AVD\nпо умолчанию", command=self.save_avd_settings).pack(side="right", padx=5)

        # Подконтейнер для кнопок управления
        buttons_frame = tk.Frame(control_inner_frame)
        buttons_frame.pack(side="left", padx=20)

        # Кнопка запуска автоматизации
        self.start_button = tk.Button(
            buttons_frame,
            text="Запустить\nавтоматизацию",
            command=self.start_automation,
            font=self.custom_font,
        )
        self.start_button.pack(side="left", padx=10)

        # Кнопка завершения программы с очисткой ресурсов во время ее выполнения
        self.close_program_button = tk.Button(
            buttons_frame,
            text="Завершить во время\nавтоматизации эмуляторов",
            command=lambda: self.app.terminate_program_during_automation(self),
            font=self.custom_font,
        )
        self.close_program_button.pack(side="left", padx=10)

        # Кнопка принудительного завершения программы
        self.exit_button = tk.Button(
            buttons_frame,
            text="Завершить процесс\n(Принудительно)",
            command=self.exit_app,
            font=self.custom_font,
        )
        self.exit_button.pack(side="left", padx=10)


    def get_all_local_environ_variables(self):
        self.run_task_in_thread(
            task=LocalVariablesManager.get_all_local_env_vars,
            should_exit=False
        )

    def setup_appium_and_uiautomator2(self):
        """
        Скачиваем, распаковываем архив с бинарниками и библиотеками Node.js, добавляем в PATH.
        """
        self.run_task_in_thread(
            task=self.logic.setup_appium_and_uiautomator2,
            should_exit=False
        )

    def download_and_setup_java_sdk_and_android_sdk_tools(self):
        self.run_task_in_thread(
            task=self.logic.download_and_setup_java_sdk_and_android_sdk_tools,
            should_exit=False
        )

    def download_and_setup_node_js(self):
        """
        Скачиваем, распаковываем архив с бинарниками и библиотеками Node.js, добавляем в PATH.
        """
        self.run_task_in_thread(
            task=self.logic.download_and_setup_node_js,
            should_exit=False
        )

    def check_if_is_node_installed(self):
        """
        Проверяем установлен ли NODE JS и уведомляем об этом пользователя.
        """
        if self.logic.check_if_is_node_installed():
            messagebox.showinfo("Проверка прошла успешно", "NodeJS уже установлен на вашем ПК.")
        else:
            messagebox.showinfo("Требуется установка NodeJS", "NodeJS еще НЕ установлен на вашем ПК\n"
                                                              "Требуется установка для успешной работы\n"
                                                              "с установщиком Appium.")


    def save_default_threads_amount(self):
        self.logic.save_threads_config(num_threads=self.num_threads.get())


    def save_avd_settings(self):
        self.logic.set_avd_property("ram_size", self.ram_size.get())
        self.logic.set_avd_property("disk_size", self.disk_size.get())
        self.logic.set_avd_property("emulator_ready_timeout", self.avd_ready_timeout.get())
        logger.info("Настройки AVD сохранены.")


    def restart_adb_server(self):
        self.run_task_in_thread(
            task=self.logic.restart_adb_server,
            should_exit=False
        )


    def forced_to_exit_app(self):
        if messagebox.askyesno("Подтверждение", "На данном этапе программу\n"
                                                "необходимо завершить,\n"
                                                "чтобы применились изменения\n"
                                                "глобальных переменных\n"
                                                "Запустите ее снова вручную."):
            try:
                self.app.perform_exit()
            except Exception as e:
                logger.error(f"Ошибка при вызове перезапуска: {e}")
                messagebox.showerror("Ошибка", "Не удалось перезапустить программу.")


    def exit_app(self):
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите\n"
                                                "принудительно завершить программу?\n"
                                                "Может потребоваться вручную\n"
                                                "завершить работу эмуляторов, если они запущены.\n"
                                                "(только в крайних случаях)"):
            try:
                self.app.perform_exit()
            except Exception as e:
                logger.error(f"Ошибка при вызове перезапуска: {e}")
                messagebox.showerror("Ошибка", "Не удалось перезапустить программу.")


    def clear_tools_files_cache(self):
        self.logic.clear_tools_files_cache()


    def run_task_in_thread(self, task, *args, should_exit=True, **kwargs):
        """
        Запускает задачу в отдельном потоке, отключая интерфейс на время выполнения.
        :param task: Функция задачи.
        :param args: Позиционные аргументы для задачи.
        :param kwargs: Именованные аргументы для задачи.
        :param should_exit: Если True, вызывает self.forced_to_exit_app() после завершения задачи.
        """

        def task_wrapper():
            try:
                # Выполняем задачу с переданными аргументами
                task(*args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка при выполнении задачи: {e}")
                messagebox.showerror("Ошибка", f"Произошла ошибка: {e}")
            finally:
                self.enable_all_widgets()
                self.loading_indicator.hide_loading_indicator()
                if should_exit:
                    self.forced_to_exit_app()

        # Отключаем все виджеты перед запуском задачи
        self.disable_all_widgets()

        # Запускаем задачу в отдельном потоке
        self.loading_indicator.show_loading_indicator()
        thread = threading.Thread(target=task_wrapper, daemon=True)
        thread.start()

    def start_automation(self):
        """
        Закрывает главное окно, запускает автоматизацию.
        """
        # Отключаем кнопку
        if self.logic.verify_environment_setup() and self.logic.are_required_flags_set() and self.start_button:
            self.start_button.config(state=tk.DISABLED)

            automation_thread = Thread(target=self.app.run_multithreaded_automation, daemon=True)    # Запускаем автоматизацию
            automation_thread.start()

    def disable_terminate_button(self):
        # Отключаем кнопку
        if self.close_program_button:
            self.close_program_button.config(state=tk.DISABLED)

    def reset_all_authorizations(self):
        """
        Сбрасываем статус авторизации на False для всех AVD в конфигурации.
        """
        if not os.path.exists(self.logic.avd_list_info_config_file):
            messagebox.showinfo("Информация", "Конфигурационный файл не найден.")
            return
        if messagebox.askyesno("Подтверждение", "Вы действительно хотите сбросить\nавторизацию для всех эмуляторов?"):
            self.logic.emulator_auth_config_manager.reset_all_authorizations()

    def delete_config(self):
        """Удаляет конфигурационный файл с подтверждением пользователя."""
        if not os.path.exists(self.logic.avd_list_info_config_file):
            messagebox.showinfo("Информация", "Конфигурационный файл не найден.")
            return

        # Подтверждение удаления
        confirm = messagebox.askyesno("Удаление конфигурации", "Уверены, что хотите удалить текущий конфиг?")
        if confirm:
            try:
                os.remove(self.logic.avd_list_info_config_file)
                messagebox.showinfo("Успех", "Конфигурационный файл успешно удален.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить конфигурационный файл: {e}")

    def show_config(self):
        """Открывает окно с содержимым конфигурационного файла."""
        config_content = self.logic.load_config_file_content()

        if config_content:
            messagebox.showinfo(title="Cодержимое конфига",
                                message=json.dumps(config_content, ensure_ascii=False, indent=4))
        else:
            messagebox.showinfo(title="Конфигурация пуста",
                                message="Конфигурация пуста или файл отсутствует.")

    def show_existing_avds_list(self):
        """ Открывает окно со списком созданных AVD. """
        if self.logic.verify_environment_setup():
            avd_list = self.logic.emulator_manager.get_avd_list()

            if avd_list and not avd_list == []:
                avd_list_text = "\n".join(avd_list)
                messagebox.showinfo(title="Список созданных AVD", message=avd_list_text)
            else:
                messagebox.showinfo(title="Пустой список AVD", message="Список созданных AVD пуст.")

    def delete_all_avds(self):
        """ Удаляет все существующие AVD через вызов метода в логике. """

        if self.logic.verify_environment_setup():
            avd_list = self.logic.emulator_manager.get_avd_list()  # Получаем список AVD

            if not avd_list or avd_list == []:
                messagebox.showinfo(
                    title="Информация",
                    message="Нет доступных AVD для удаления."
                )
                return

            avd_list_text = "\n".join(avd_list)
            if messagebox.askyesno(
                    title="Подтверждение",
                    message=f"Вы уверены, что хотите удалить все AVD?\n{avd_list_text}"
            ):
                try:
                    self.run_task_in_thread(
                        task=self.logic.delete_all_avds,
                        should_exit=False
                    )
                    os.remove(self.logic.avd_list_info_config_file)
                    messagebox.showinfo("Успех", "Все AVD успешно удалены.\nТакже удален конфиг.")
                except Exception as e:
                    logger.error(f"Ошибка при удалении AVD: {e}")
                    messagebox.showerror("Ошибка", f"Не удалось удалить все AVD: {e}")


    def browse_excel_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx"),
                                                          ("Excel files", "*.xlsm"),
                                                          ("Excel files", "*.xls")])
        if file_path:
            self.source_excel_file_path.set(file_path)
            self.set_export_table_path()
            self.refresh_excel_table()


    def refresh_excel_table(self):
        """
        Обновляет содержимое Treeview с данными из файла Excel.
        """
        file_path = self.source_excel_file_path.get()
        if not file_path or not os.path.isfile(file_path):
            messagebox.showerror("Ошибка", "Файл таблицы Excel не найден!")
            return

        try:
            # Получаем данные через логику
            df = self.logic.load_excel_data(file_path)

            # Очищаем Treeview
            self.excel_treeview.delete(*self.excel_treeview.get_children())

            # Устанавливаем заголовки колонок
            self.excel_treeview["columns"] = list(df.columns)
            for col in df.columns:
                self.excel_treeview.heading(col, text=col)
                self.excel_treeview.column(col, anchor="w")
                self.excel_treeview.config(height=min(len(df), 8))

            # Добавляем строки в таблицу
            for _, row in df.iterrows():
                self.excel_treeview.insert("", "end", values=list(row))

            # Настраиваем ширину колонок
            column_widths = self.logic.get_column_widths(df)
            for col, width in column_widths.items():
                self.excel_treeview.column(col, width=width * 7)  # Умножаем на 7 для масштабирования

            # Настраиваем ширину окна
            self.adjust_window_width()

        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))


    def set_export_table_path(self):
        """Устанавливает путь для итоговой таблицы."""
        input_path = self.source_excel_file_path.get()
        if input_path:
            # Формируем путь для экспортного файла
            base, ext = os.path.splitext(input_path)
            export_path = f"{base}_export{ext}"
            self.export_table_path.set(export_path)


    @staticmethod
    def open_in_explorer(path_var):
        """Открывает папку в проводнике, игнорируя наличие файла."""
        path = path_var.get()
        folder_to_open = path if os.path.isdir(path) else os.path.dirname(path)  # Извлекаем папку
        if os.path.exists(folder_to_open):
            os.startfile(folder_to_open)
        else:
            messagebox.showerror("Ошибка", "Указанная папка не найдена!")


    def adjust_window_width(self):
        """Настраивает ширину окна приложения в зависимости от ширины таблицы."""
        total_width = sum(int(self.excel_treeview.column(col, "width")) for col in self.excel_treeview["columns"])
        window_width = min(total_width + 75, 1250)  # Ограничение до 1250 пикселей
        self.root.geometry(f"{window_width}x725")


    def disable_all_widgets(self):
        """
        Отключает (state=tk.DISABLED) все элементы интерфейса для предотвращения взаимодействия.
        """
        self.widget_states = {}  # Сохраняем состояния виджетов, чтобы восстановить их позже

        def disable_children(widget):
            """
            Рекурсивно отключает все дочерние элементы виджета.
            """
            for child in widget.winfo_children():
                try:
                    # Если виджет имеет атрибут state, сохраняем его состояние и отключаем
                    self.widget_states[child] = child["state"]
                    child.config(state=tk.DISABLED)
                except tk.TclError:
                    # Если у виджета нет атрибута state, игнорируем
                    pass
                # Рекурсивно обрабатываем дочерние виджеты
                disable_children(child)

        # Отключаем все элементы интерфейса
        disable_children(self.root)
        logger.info("--- Все элементы интерфейса отключены. ---")


    def enable_all_widgets(self):
        """
        Включает (state=tk.NORMAL) все элементы интерфейса для взаимодействия.
        """
        def enable_children(widget):
            """
            Рекурсивно включает все дочерние элементы виджета.
            """
            for child in widget.winfo_children():
                try:
                    # Если виджет был отключен, восстанавливаем его состояние
                    if child in self.widget_states:
                        child.config(state=self.widget_states[child])
                except tk.TclError:
                    # Если у виджета нет атрибута state, игнорируем
                    pass
                # Рекурсивно обрабатываем дочерние виджеты
                enable_children(child)

        # Включаем все элементы интерфейса
        enable_children(self.root)
        logger.info("--- Все элементы интерфейса включены обратно. ---")


class LoadingIndicator:
    def __init__(self, root):
        """
        Инициализация класса индикатора загрузки.
        :param root: Главное окно (tk.Tk).
        """
        self.root = root
        self.loading_overlay = None
        self.update_job = None  # ID задачи для обновления положения окна

        # Привязка событий для обработки сворачивания и разворачивания
        self.root.bind("<Unmap>", self._on_root_minimized)
        self.root.bind("<Map>", self._on_root_restored)


    def show_loading_indicator(self):
        """
        Отображает индикатор загрузки поверх основного окна.
        """
        if self.loading_overlay and self.loading_overlay.winfo_exists():
            return  # Окно уже отображается

        # Создаем новое окно поверх root
        self.loading_overlay = tk.Toplevel(self.root)
        self.loading_overlay.overrideredirect(True)  # Убираем рамки
        self.loading_overlay.attributes("-alpha", 0.8)  # Полупрозрачность
        self.loading_overlay.configure(bg="gray")

        # Привязка окна к root (делает его дочерним)
        self.loading_overlay.transient(self.root)
        self.loading_overlay.grab_set()  # Блокирует взаимодействие с root

        # Расчет размеров и позиции окна
        self._update_overlay_geometry()

        # Фрейм для содержимого
        frame = tk.Frame(self.loading_overlay, bg="gray")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # Элементы интерфейса (текст и анимация)
        loading_label = ttk.Label(frame, text="⏳", font=("Arial", 40))
        loading_label.pack()
        loading_text = ttk.Label(frame, text="Загрузка...", font=("Arial", 14))
        loading_text.pack()

        # Начинаем обновление положения окна
        self._schedule_position_update()


    def hide_loading_indicator(self):
        """
        Скрывает индикатор загрузки.
        """
        if self.update_job:
            self.root.after_cancel(self.update_job)  # Отменяем обновление позиции
            self.update_job = None

        if self.loading_overlay and self.loading_overlay.winfo_exists():
            self.loading_overlay.destroy()  # Уничтожаем окно
            self.loading_overlay = None


    def _update_overlay_geometry(self):
        """
        Обновляет размеры и позицию окна загрузки.
        """
        if not self.loading_overlay or not self.loading_overlay.winfo_exists():
            return

        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()

        # Расчет размеров окна загрузки (15% от размеров root)
        overlay_width = int(root_width * 0.15)
        overlay_height = int(root_height * 0.15)

        # Расчет позиции окна загрузки для центрирования
        overlay_x = self.root.winfo_x() + (root_width - overlay_width) // 2
        overlay_y = self.root.winfo_y() + (root_height - overlay_height) // 2

        # Установка размеров и позиции
        self.loading_overlay.geometry(f"{overlay_width}x{overlay_height}+{overlay_x}+{overlay_y}")


    def _schedule_position_update(self):
        """
        Планирует обновление положения окна загрузки.
        """
        self._update_overlay_geometry()
        self.update_job = self.root.after(10, self._schedule_position_update)  # Обновляем каждые 50 мс


    def _on_root_minimized(self, event):
        """
        Обработчик события сворачивания главного окна.
        """
        if self.loading_overlay and self.loading_overlay.winfo_exists():
            self.loading_overlay.withdraw()  # Скрываем окно загрузки


    def _on_root_restored(self, event):
        """
        Обработчик события разворачивания главного окна.
        """
        try:
            if self.loading_overlay and self.loading_overlay.winfo_exists():
                self.loading_overlay.deiconify()  # Показываем окно загрузки
        except Exception as ex:
            logger.info(ex)
