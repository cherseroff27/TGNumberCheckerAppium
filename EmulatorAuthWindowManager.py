from threading import Lock
from threading import Event
import tkinter as tk
import tkinter.font as tk_font


class EmulatorAuthWindowManager:
    def __init__(self, root):
        self.root = root
        self.lock = Lock()  # Для защиты от одновременного изменения окон
        self.windows = {}

        self.header_font = tk_font.Font(family="Helvetica", size=12, weight="bold")
        self.custom_font = tk_font.Font(family="Calibri", size=12, weight="normal")

    def show_auth_window(self, avd_name):
        """Создает окно авторизации для эмулятора."""
        event = Event()  # Событие, которое будет сигнализировать об авторизации

        def create_window():
            with self.lock:
                if avd_name in self.windows:
                    return  # Окно уже открыто

                # Создаём окно
                window = tk.Toplevel(self.root)
                window.title(f"Ручная авторизация: {avd_name}")
                window.geometry("400x150")

                # Вывод окна на передний план
                window.attributes("-topmost", True)  # Устанавливаем окно поверх других
                window.focus_force()  # Ставим фокус на окно
                window.grab_set()  # Захватываем управление вводом для этого окна

                label = tk.Label(window, text=f"Авторизуйтесь ВРУЧНУЮ\nв эмуляторе {avd_name}.\n"
                                              f"Подтвердите нажатием по кнопке.", font=self.header_font)
                label.pack(pady=10)

                button = tk.Button(
                    window,
                    text="Авторизовался\nприложении Telegram.",
                    command=lambda: self._confirm_auth(avd_name, event, window),
                    font=self.custom_font
                )
                button.pack(pady=10)

                self.windows[avd_name] = window

        # Вызов создания окна в основном потоке
        self.root.after(0, create_window)
        return event

    def _confirm_auth(self, avd_name, event, window):
        """Закрывает окно и уведомляет поток о завершении авторизации."""
        with self.lock:
            if avd_name in self.windows:
                del self.windows[avd_name]
        event.set()  # Сигнализируем, что пользователь подтвердил авторизацию
        window.destroy()
