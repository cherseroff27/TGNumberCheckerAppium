import json
import logging
import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


class TelegramCheckerUI:
    def __init__(self, root, logic, app):
        self.app = app
        self.root = root
        self.logic = logic
        self.root.title("Telegram Number Checker")
        self.root.geometry("1200x900")

        self.num_threads = tk.IntVar(value=1)  # Устанавливаем количество потоков по умолчанию 1

        # Интерфейсные переменные
        latest_excel_file = logic.get_latest_excel_file()
        export_excel_file = logic.get_export_table_path(latest_excel_file)

        self.source_excel_file_path = tk.StringVar(value=latest_excel_file)
        self.export_table_path = tk.StringVar(value=export_excel_file)

        # Таблицы
        self.excel_frame = ttk.Frame(self.root)
        self.export_frame = ttk.Frame(self.root)
        self.excel_treeview = ttk.Treeview(columns=[], show="headings")

        # Поле для ввода количества потоков
        self.threads_entry = ttk.Entry(self.root, width=10, textvariable=self.num_threads)
        # Создаем виджеты
        self.create_widgets()
        # Автозагрузка таблиц и профилей
        self.refresh_excel_table()

    def create_widgets(self):
        # Кнопка для показа конфигурации
        ttk.Button(self.root, text="Показать конфигурацию AVD", command=self.show_config).pack(pady=5)

        # Кнопка для удаления конфигурации
        ttk.Button(self.root, text="Удалить конфигурацию", command=self.delete_config).pack(pady=5)

        # Кнопка для сброса флага авторизации у всех эмуляторов в конфиге
        ttk.Button(self.root, text="Сбросить флаг авторизации у всех эмуляторов в конфиге", command=self.reset_all_authorizations()).pack(pady=5)

        # Файл Excel
        ttk.Label(self.root, text="Файл таблицы Excel:", font=("Arial", 12)).pack(pady=5)

        # Кнопка обновления содержимого Excel-файла
        ttk.Button(self.excel_frame, text="Обновить\nтаблицу", command=self.refresh_excel_table).pack(side="left", padx=5)
        ttk.Entry(self.excel_frame, textvariable=self.source_excel_file_path, width=50).pack(side="left", fill="x", expand=True, padx=5)
        # Кнопка выбрать файл
        ttk.Button(self.excel_frame, text="Выбрать\nфайл", command=self.browse_excel_file).pack(side="left", padx=5)
        # Кнопка открывающая выбранный файл таблицы в проводнике
        ttk.Button(self.excel_frame, text="Открыть\nв проводнике", command=lambda: self.open_in_explorer(self.source_excel_file_path)).pack(side="left", padx=5)
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
        Закрывает главное окно, запускает автоматизацию.
        """
        self.root.destroy()  # Закрываем главное окно
        self.app.run_multithreaded_automation()  # Запускаем автоматизацию


    def reset_all_authorizations(self):
        """
        Сбрасываем статус авторизации на False для всех AVD в конфигурации.
        """
        if not os.path.exists(self.logic.config_file):
            messagebox.showinfo("Информация", "Конфигурационный файл не найден.")
            return
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
        self.root.geometry(f"{window_width}x900")
