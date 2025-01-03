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
        """Создает окно авторизации для эмулятора с таймером."""
        event = Event()  # Событие, которое будет сигнализировать об авторизации
        timeout_seconds = 600  # 10 минут в секундах
        remaining_time = [timeout_seconds]  # Списком для изменения внутри вложенной функции

        def create_window():
            with self.lock:
                if avd_name in self.windows:
                    return  # Окно уже открыто

                # Создаём окно
                window = tk.Toplevel(self.root)
                window.title(f"Ручная авторизация: {avd_name}")
                window.geometry("400x275")

                # Вывод окна на передний план
                window.attributes("-topmost", True)  # Устанавливаем окно поверх других
                window.focus_force()  # Ставим фокус на окно

                label = tk.Label(
                    window,
                    text=f"Авторизуйтесь ВРУЧНУЮ\nв эмуляторе {avd_name}.\n"
                         f"Подтвердите нажатием кнопки.",
                    font=self.header_font
                )
                label.pack(pady=10)

                timer_label = tk.Label(window, text="", font=self.custom_font)
                timer_label.pack(pady=5)

                button = tk.Button(
                    window,
                    text="Авторизовался\nв приложении Telegram.",
                    command=lambda: self._confirm_auth(avd_name, event, window),
                    font=self.custom_font
                )
                button.pack(pady=10)

                self.windows[avd_name] = window

                def update_timer():
                    if remaining_time[0] > 0:
                        minutes, seconds = divmod(remaining_time[0], 60)
                        timer_label.config(text=f"Сессия Appium Server будет поддерживаться\n"
                                                f"в течение {int(timeout_seconds/60)} минут.\n"
                                                f"Осталось времени: {minutes:02}:{seconds:02}.\n"
                                                f"Авторизуйтесь в течение этого времени!!!")
                        remaining_time[0] -= 1
                        window.after(1000, update_timer)
                    else:
                        self._timeout_handler(avd_name, window)
                # Запуск таймера
                update_timer()

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


    def _timeout_handler(self, avd_name, window):
        """Обрабатывает истечение времени авторизации."""
        with self.lock:
            if avd_name in self.windows:
                del self.windows[avd_name]
        print(f"Сессия Appium для {avd_name} завершена из-за бездействия.")
        window.destroy()
