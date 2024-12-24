import json
import os
import tkinter as tk
from threading import Thread
from tkinter import filedialog, ttk, messagebox
import tkinter.font as tk_font


from logger_config import Logger
logger = Logger.get_logger(__name__)


class TelegramCheckerUI:
    def __init__(self, root, logic, app):
        self.app = app
        self.root = root
        self.logic = logic
        self.root.title("Telegram Number Checker")
        self.root.geometry("1200x900")

        self.header_font = tk_font.Font(family="Helvetica", size=12, weight="bold")
        self.custom_font = tk_font.Font(family="Calibri", size=11, weight="normal")

        self.saved_config = self.logic.load_threads_config()
        default_threads = self.saved_config.get("num_threads", 1)
        self.num_threads = tk.IntVar(value=default_threads)  # Устанавливаем количество потоков по умолчанию default_threads

        # Интерфейсные переменные
        latest_excel_file = logic.get_latest_excel_file()
        export_excel_file = logic.get_export_table_path(latest_excel_file)

        self.source_excel_file_path = tk.StringVar(value=latest_excel_file)
        self.export_table_path = tk.StringVar(value=export_excel_file)

        # Таблицы
        self.excel_frame = ttk.Frame(self.root)
        self.export_frame = ttk.Frame(self.root)
        self.excel_treeview = ttk.Treeview(columns=[], show="headings", height=5)

        # Поле для ввода количества потоков
        self.threads_entry = ttk.Entry(self.root, width=10, textvariable=self.num_threads)

        self.start_button = None
        self.close_program_button = None

        # Создаем виджеты
        self.create_widgets()
        # Автозагрузка таблиц и профилей
        self.refresh_excel_table()

    def create_widgets(self):
        # Контейнер для первых четырех кнопок
        top_buttons_frame = tk.Frame(self.root)
        top_buttons_frame.pack(fill="x", pady=5)

        # Центрирование кнопок в контейнере
        top_buttons_inner_frame = tk.Frame(top_buttons_frame)
        top_buttons_inner_frame.pack(anchor="center")

        # Добавляем кнопки в контейнер
        tk.Button(top_buttons_inner_frame, text="Показать содержимое\nконфига AVD", font=self.custom_font, justify="center", command=self.show_config).pack(side="left", padx=5)
        tk.Button(top_buttons_inner_frame, text="Удалить конфиг\n(Информация об AVD)", font=self.custom_font, justify="center", command=self.delete_config).pack(side="left", padx=5)
        tk.Button(top_buttons_inner_frame, text="Сбросить флаг авторизации\nу всех AVD в конфиге", font=self.custom_font, justify="center", command=self.reset_all_authorizations).pack(side="left", padx=5)
        tk.Button(top_buttons_inner_frame, text="Удалить все AVD\n(Созданные AVD)", font=self.custom_font, justify="center", command=self.delete_all_avds).pack(side="left", padx=5)

        # Файл Excel
        tk.Label(self.root, text="Файл таблицы Excel:", font=self.header_font).pack(pady=5)

        # Кнопка обновления содержимого Excel-файла
        tk.Button(self.excel_frame, text="Обновить\nтаблицу", font=self.custom_font, command=self.refresh_excel_table).pack(side="left", padx=3)
        tk.Entry(self.excel_frame, textvariable=self.source_excel_file_path, font=self.custom_font, width=50).pack(side="left", fill="x", expand=True, padx=5)
        # Кнопка выбрать файл
        tk.Button(self.excel_frame, text="Выбрать\nфайл", font=self.custom_font, command=self.browse_excel_file).pack(side="left", padx=5)
        # Кнопка открывающая выбранный файл таблицы в проводнике
        tk.Button(self.excel_frame, text="Открыть\nв проводнике", font=self.custom_font, command=lambda: self.open_in_explorer(self.source_excel_file_path)).pack(side="left", padx=5)
        self.excel_frame.pack(fill="x", padx=10, pady=5)


        # Поле для итогового файла
        tk.Label(self.root, text="Итоговый файл таблицы Excel:", font=self.header_font).pack(pady=5)
        tk.Entry(self.export_frame, textvariable=self.export_table_path, font=self.custom_font, width=50).pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(self.export_frame, text="Открыть\nв проводнике", font=self.custom_font, command=lambda: self.open_in_explorer(self.export_table_path)).pack(side="left", padx=5)
        self.export_frame.pack(fill="x", padx=10, pady=5)

        # Содержимое таблицы Excel
        tk.Label(self.root, text="Содержимое таблицы Excel:", font=self.header_font).pack(pady=5)
        self.excel_treeview.pack(fill="both", expand=True, padx=10, pady=5)


        # Добавляем контейнер для секции потоков и кнопок управления
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill="x", pady=5)

        # Центрирование элементов в контейнере
        control_inner_frame = tk.Frame(control_frame)
        control_inner_frame.pack(anchor="center")

        # Поле для ввода количества потоков
        tk.Label(control_inner_frame, text="Количество потоков:", font=self.header_font).pack(side="left", padx=10)
        self.threads_entry = ttk.Entry(control_inner_frame, width=10, textvariable=self.num_threads)
        self.threads_entry.pack(side="left", padx=5)

        # Кнопка завершения программы
        self.close_program_button = tk.Button(
            control_inner_frame,
            text="Завершить программу и очистить ресурсы",
            command=lambda: self.app.terminate_program(self),
            font=self.custom_font,
        )
        self.close_program_button.pack(side="left", padx=10)

        # Кнопка запуска автоматизации
        self.start_button = tk.Button(
            control_inner_frame,
            text="Запустить автоматизацию",
            command=self.start_automation,
            font=self.custom_font,
        )
        self.start_button.pack(side="left", padx=10)


    def start_automation(self):
        """
        Закрывает главное окно, запускает автоматизацию.
        """
        # Отключаем кнопку
        if self.start_button:
            self.start_button.config(state=tk.DISABLED)

        # self.root.destroy()  # Закрываем главное окно
        automation_thread = Thread(target=self.app.run_multithreaded_automation, daemon=True)    # Запускаем автоматизацию
        # self.root.withdraw()
        automation_thread.start()


    def disable_terminate_button(self):
        # Отключаем кнопку
        if self.close_program_button:
            self.close_program_button.config(state=tk.DISABLED)
        self.logic.save_threads_config(num_threads=self.num_threads.get())


    def reset_all_authorizations(self):
        """
        Сбрасываем статус авторизации на False для всех AVD в конфигурации.
        """
        if not os.path.exists(self.logic.config_file):
            messagebox.showinfo("Информация", "Конфигурационный файл не найден.")
            return
        if messagebox.askyesno("Подтверждение", "Вы действительно хотите сбросить авторизацию для всех эмуляторов?"):
            self.logic.emulator_auth_config_manager.reset_all_authorizations()


    def delete_config(self):
        """Удаляет конфигурационный файл с подтверждением пользователя."""
        if not os.path.exists(self.logic.config_file):
            messagebox.showinfo("Информация", "Конфигурационный файл не найден.")
            return

        # Подтверждение удаления
        confirm = messagebox.askyesno("Удаление конфигурации", "Уверены, что хотите удалить текущий конфиг?")
        if confirm:
            try:
                os.remove(self.logic.config_file)
                messagebox.showinfo("Успех", "Конфигурационный файл успешно удален.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить конфигурационный файл: {e}")


    def show_config(self):
        """Открывает окно с содержимым конфигурационного файла."""
        config_content = self.logic.load_config_file_content()

        config_window = tk.Toplevel(self.root)
        config_window.title("Содержимое конфигурации")
        config_window.geometry("500x300")

        text_widget = tk.Text(config_window, wrap=tk.WORD)
        text_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        if config_content:
            text_widget.insert(tk.END, json.dumps(config_content, ensure_ascii=False, indent=4))
        else:
            text_widget.insert(tk.END, "Конфигурация пуста или файл отсутствует.")

        text_widget.config(state=tk.DISABLED)


    def delete_all_avds(self):
        """
        Удаляет все существующие AVD через вызов метода в логике.
        """
        avd_list = self.logic.emulator_manager.get_avd_list()  # Получаем список AVD

        if not avd_list:
            messagebox.showinfo("Информация", "Нет доступных AVD для удаления.")
            return

        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить все AVD?"):
            try:
                self.logic.delete_all_avds()  # Метод логики для удаления AVD
                self.delete_config()
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
                self.excel_treeview.config(height=min(len(df), 10))

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
        window_width = min(total_width + 40, 1250)  # Ограничение до 1250 пикселей
        self.root.geometry(f"{window_width}x600")
