import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os

class ScriptManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Script Manager")
        self.script_path = None
        self.process = None

        # Создаем элементы интерфейса
        self.label = tk.Label(root, text="Выберите путь к скрипту:")
        self.label.pack(pady=10)

        self.path_entry = tk.Entry(root, width=50)
        self.path_entry.pack(pady=5)

        self.browse_button = tk.Button(root, text="Обзор", command=self.browse_script)
        self.browse_button.pack(pady=5)

        self.start_button = tk.Button(root, text="Запустить скрипт", command=self.start_script, state=tk.DISABLED)
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(root, text="Остановить скрипт", command=self.stop_script, state=tk.DISABLED)
        self.stop_button.pack(pady=10)

        self.log_label = tk.Label(root, text="Логи скрипта:")
        self.log_label.pack(pady=10)

        self.log_text = tk.Text(root, width=80, height=20, state=tk.DISABLED)
        self.log_text.pack(pady=5)

    def browse_script(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
        if file_path:
            self.script_path = file_path
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, file_path)
            self.start_button.config(state=tk.NORMAL)

    def start_script(self):
        if not self.script_path or not os.path.isfile(self.script_path):
            messagebox.showerror("Ошибка", "Пожалуйста, выберите корректный скрипт.")
            return

        if self.process is None:
            # Запускаем скрипт как отдельный процесс
            self.process = subprocess.Popen(
                ["python", self.script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP  # Для Windows
            )

            # Переключаем состояние кнопок
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

            # Поток для чтения логов
            threading.Thread(target=self.read_logs, daemon=True).start()

    def read_logs(self):
        if self.process:
            for line in iter(self.process.stdout.readline, b''):
                self.append_log(line.decode('utf-8'))
            self.process.stdout.close()

    def append_log(self, text):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)  # Автопрокрутка вниз
        self.log_text.config(state=tk.DISABLED)

    def stop_script(self):
        if self.process:
            # Завершаем процесс
            self.process.terminate()
            self.process.wait()  # Дожидаемся завершения процесса
            self.process = None

            # Переключаем состояние кнопок
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)


    def on_close(self):
        # Обрабатываем закрытие окна
        if self.process:
            self.stop_script()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScriptManagerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
