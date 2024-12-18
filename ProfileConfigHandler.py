import os
import json

class ProfileConfigHandler:
    CONFIG_FILE = "profiles.json"

    def __init__(self):
        # Если конфигурационный файл не существует, создаем его с пустым JSON
        if not os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump({}, f,  ensure_ascii=False, indent=4)

    def is_authorized(self, profile_name):
        # Читаем текущие профили из файла.
        with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        # Проверяем, авторизован ли указанный профиль.
        return profiles.get(profile_name, {}).get("authorized", False)

    def mark_as_authorized(self, profile_name):
        # Обновляем статус авторизации профиля.
        with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        profiles[profile_name] = {"authorized": True}
        # Записываем изменения обратно в файл.
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, ensure_ascii=False, indent=4)

    def get_all_profiles(self):
        with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
