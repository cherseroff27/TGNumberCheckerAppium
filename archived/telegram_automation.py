from pywinauto import Application

# Запускаем Telegram Desktop
app = Application(backend="uia").start(r"C:\Users\cherseroff\AppData\Roaming\Telegram Desktop\Telegram.exe", timeout=10)
app.connect(best_match="Telegram", timeout=10)
# Подключаемся к основному окну приложения Telegram
main_window = app.window(title_re=".*Telegram")

# Даем время приложению загрузиться
main_window.wait('visible', timeout=10)

print("Успешно подключились к окну Telegram.")

children = main_window.child_window(control_type="Group").children()
for child in children:
    print(child.window_text(), child.class_name())
