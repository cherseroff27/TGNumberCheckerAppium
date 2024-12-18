import os
import shutil
import tkinter as tk
from tkinter import filedialog, ttk, messagebox


class TelegramCheckerUI:
    def __init__(self, root, logic, app):
        self.app = app
        self.root = root
        self.logic = logic
        self.root.title("Telegram Number Checker")
        self.root.geometry("1200x900")

        # Переменная для названия нового профиля браузера
        self.new_profile_name = tk.StringVar()
        self.num_threads = tk.IntVar(value=1)  # Устанавливаем количество потоков по умолчанию 1
        self.placeholder_text = "Введите имя профиля"

        # Контейнер для полей ввода и кнопок
        self.browser_frame = ttk.Frame(self.root)
        self.new_profile_entry = tk.Entry(self.browser_frame, textvariable=self.new_profile_name, width=20)

        # Интерфейсные переменные
        latest_excel_file = logic.get_latest_excel_file()
        export_excel_file = logic.get_export_table_path(latest_excel_file)

        self.browser_profiles_dir = tk.StringVar(value=logic.get_profiles_dir())
        self.excel_file_path = tk.StringVar(value=latest_excel_file)
        self.export_table_path = tk.StringVar(value=export_excel_file)

        # Таблицы
        self.excel_frame = ttk.Frame(self.root)
        self.export_frame = ttk.Frame(self.root)
        self.excel_treeview = ttk.Treeview(columns=[], show="headings")
        self.profiles_treeview = ttk.Treeview(columns=["Profile Name"], show="headings")

        # Поле для ввода количества потоков
        self.threads_entry = ttk.Entry(self.root, width=10, textvariable=self.num_threads)

        # Создаем виджеты
        self.create_widgets()
        # Автозагрузка таблиц и профилей
        self.refresh_excel_table()
        self.load_default_profiles()

    def create_widgets(self):
        # Папка профилей браузера
        ttk.Label(self.root, text="Папка профилей браузера:", font=("Arial", 12)).pack(pady=5)

        # Кнопка обновления профилей
        ttk.Button(self.browser_frame, text="Обновить\nсписок профилей", command=self.refresh_profiles_table).pack(side="left", padx=5)
        self.browser_frame.pack(fill="x", padx=10, pady=5)

        # Поле для имени нового профиля с placeholder
        self.new_profile_entry.pack(side="left", padx=5)
        ttk.Button(self.browser_frame, text="Создать\nпрофиль", command=self.create_new_profile).pack(side="left", padx=5)
        ttk.Button(self.browser_frame, text="Удалить\nпрофиль", command=self.delete_selected_profile).pack(side="left", padx=5)
        ttk.Entry(self.browser_frame, textvariable=self.browser_profiles_dir, width=20).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(self.browser_frame, text="Выбрать\nпапку", command=self.browse_profiles_dir).pack(side="left", padx=5)

        # Привязываем события для placeholder
        self.new_profile_entry.bind("<FocusIn>", self.clear_placeholder)
        self.new_profile_entry.bind("<FocusOut>", self.add_placeholder)
        self.set_placeholder()  # Устанавливаем placeholder сразу при создании

        # Содержимое папки профилей браузеров
        ttk.Label(self.root, text="Содержимое папки профилей браузеров:", font=("Arial", 12)).pack(pady=10)
        self.profiles_treeview.pack(fill="both", expand=True, padx=10, pady=10)
        self.profiles_treeview.heading("Profile Name", text="Profile Name")
        self.profiles_treeview.column("Profile Name", anchor="w", width=300)

        # Файл Excel
        ttk.Label(self.root, text="Файл таблицы Excel:", font=("Arial", 12)).pack(pady=5)

        # Кнопка обновления содержимого Excel-файла
        ttk.Button(self.excel_frame, text="Обновить\nтаблицу", command=self.refresh_excel_table).pack(side="left", padx=5)
        ttk.Entry(self.excel_frame, textvariable=self.excel_file_path, width=50).pack(side="left", fill="x", expand=True, padx=5)
        # Кнопка выбрать файл
        ttk.Button(self.excel_frame, text="Выбрать\nфайл", command=self.browse_excel_file).pack(side="left", padx=5)
        # Кнопка открывающая выбранный файл таблицы в проводнике
        ttk.Button(self.excel_frame, text="Открыть\nв проводнике", command=lambda: self.open_in_explorer(self.excel_file_path)).pack(side="left", padx=5)
        self.excel_frame.pack(fill="x", padx=10, pady=5)


        # Поле для итогового файла
        ttk.Label(self.root, text="Итоговый файл таблицы Excel:", font=("Arial", 12)).pack(pady=5)
        ttk.Entry(self.export_frame, textvariable=self.export_table_path, width=50).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(self.export_frame, text="Открыть\nв проводнике", command=lambda: self.open_in_explorer(self.export_table_path)).pack(side="left", padx=5)
        self.export_frame.pack(fill="x", padx=10, pady=5)

        # Содержимое таблицы Excel
        ttk.Label(self.root, text="Содержимое таблицы Excel:", font=("Arial", 12)).pack(pady=5)
        self.excel_treeview.pack(fill="both", expand=True, padx=10, pady=10)

        # Раздел с кнопкой и полем для ввода количества потоков
        ttk.Label(self.root, text="Количество потоков:", font=("Arial", 12)).pack(side="left", padx=100, pady=25)
        self.threads_entry.pack(side="left", padx=5)

        # Кнопка запуска автоматизации
        ttk.Button(self.root, text="Запустить автоматизацию", command=self.start_automation).pack(side="right", padx=100, pady=25)

    def start_automation(self):
        """
        Закрывает главное окно и запускает run_multithreaded_automation.
        """
        self.root.destroy()  # Закрываем главное окно
        self.app.run_multithreaded_automation()  # Запускаем автоматизацию

    def set_placeholder(self):
        """Добавляем placeholder в Entry."""
        self.new_profile_entry.insert(0, self.placeholder_text)
        self.new_profile_entry.config(foreground="gray")

    def clear_placeholder(self, event):
        """Удаляем placeholder при фокусировке."""
        if self.new_profile_name.get() == self.placeholder_text:
            self.new_profile_entry.delete(0, tk.END)
            self.new_profile_entry.config(foreground="black")

    def add_placeholder(self, event):
        """Возвращаем placeholder, если поле пустое."""
        if not self.new_profile_name.get():
            self.set_placeholder()

    def browse_profiles_dir(self):
        directory = filedialog.askdirectory(initialdir=self.browser_profiles_dir.get())
        if directory:
            self.browser_profiles_dir.set(directory)

            # Загружаем профили в Treeview
            self.logic.browser_profiles_dir = directory
            self.logic.load_profiles_to_treeview(self.profiles_treeview)

    def browse_excel_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx"),
                                                          ("Excel files", "*.xlsm"),
                                                          ("Excel files", "*.xls")])
        if file_path:
            self.excel_file_path.set(file_path)
            self.set_export_table_path()
            self.refresh_excel_table()

    def refresh_profiles_table(self):
        """
        Обновляет содержимое Treeview для отображения профилей из дефолтной папки.
        """
        default_dir = self.browser_profiles_dir.get()
        if os.path.exists(default_dir):
            self.logic.load_profiles_to_treeview(self.profiles_treeview)

    def delete_selected_profile(self):
        """Удаляет выбранный профиль в дереве профилей."""
        selected_items = self.profiles_treeview.selection()  # Получаем кортеж идентификаторов выбранных элементов

        if not selected_items:
            messagebox.showwarning("Предупреждение", "Выберите профиль для удаления!")
            return

        if len(selected_items) > 1:
            messagebox.showwarning("Предупреждение", "Удаление нескольких профилей одновременно не поддерживается.")
            return

        selected_item = selected_items[0]  # Получаем первый (и единственный) выбранный элемент
        profile_values = self.profiles_treeview.item(selected_item, "values")

        if isinstance(profile_values, tuple) and len(profile_values) > 0:
            profile_name = profile_values[0]  # Извлекаем имя профиля
            profile_path = os.path.join(self.browser_profiles_dir.get(), profile_name)

            try:
                if os.path.exists(profile_path):
                    shutil.rmtree(profile_path)  # Удаляем профиль
                    self.profiles_treeview.delete(selected_item)  # Удаляем строку из Treeview
                    messagebox.showinfo("Успех", f"Профиль {profile_name} успешно удалён.")
                else:
                    messagebox.showwarning("Предупреждение", "Папка профиля не найдена.")
            except OSError as e:
                messagebox.showerror("Ошибка удаления", str(e))

    def create_new_profile(self):
        """Создаёт новый профиль в указанной директории."""
        profile_name = self.new_profile_name.get().strip()

        if profile_name and self.browser_profiles_dir.get():
            profile_path = os.path.join(self.browser_profiles_dir.get(), profile_name)

            try:
                if not os.path.exists(profile_path):
                    os.makedirs(profile_path)
                    self.refresh_profiles_table()
                else:
                    messagebox.showwarning("Предупреждение", "Такой профиль уже существует")
            except OSError as e:
                messagebox.showerror("Ошибка создания", str(e))

    def load_default_profiles(self):
        """
        Загружает профили из папки по умолчанию при запуске приложения.
        """
        default_dir = self.browser_profiles_dir.get()
        if os.path.exists(default_dir):
            self.logic.load_profiles_to_treeview(self.profiles_treeview)

    def refresh_excel_table(self):
        """
        Обновляет содержимое Treeview с данными из файла Excel.
        """
        file_path = self.excel_file_path.get()
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

            # Добавляем строки в таблицу
            for _, row in df.iterrows():
                self.excel_treeview.insert("", "end", values=list(row))

            # Настраиваем ширину колонок
            column_widths = self.logic.get_column_widths(df)
            for col, width in column_widths.items():
                self.excel_treeview.column(col, width=width * 7)  # Умножаем на 10 для масштабирования

            # Настраиваем ширину окна
            self.adjust_window_width()

        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))

    def set_export_table_path(self):
        """Устанавливает путь для итоговой таблицы."""
        input_path = self.excel_file_path.get()
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
        self.root.geometry(f"{window_width}x900")
