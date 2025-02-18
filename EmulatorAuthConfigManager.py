import threading
import json
import os

from logger_config import Logger
logger = Logger.get_logger(__name__)


class EmulatorAuthConfigManager:
    CONFIG_FILE = "emulator_auth_config.json"

    # noinspection PyTypeChecker
    def __init__(self):
        self.lock = threading.Lock()  # Для обеспечения потокобезопасности
        if not os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)

    def _read_config(self):
        with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    # noinspection PyTypeChecker
    def _write_config(self, config):
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            logger.info(f"Записываем конфигурацию: {config}")
            json.dump(config, f, ensure_ascii=False, indent=4)

    def is_authorized(self, avd_name):
        """Проверяем, авторизован ли эмулятор в мобильном приложении Telegram."""
        with self.lock:
            config = self._read_config()
        return config.get(avd_name, {}).get("authorized", False)

    def mark_as_authorized(self, avd_name):
        """Помечаем эмулятор как авторизованный."""
        with self.lock:
            config = self._read_config()
            config[avd_name] = {"authorized": True}
            self._write_config(config)

    def refresh_config(self):
        """Обновляет данные конфигурации из файла."""
        with self.lock:
            self.config = self._read_config()

    def reset_all_authorizations(self):
        """
        Сбрасывает все флаги 'authorized' на False во всей конфигурации.
        """
        with self.lock:
            # Обновляем данные из файла
            config = self._read_config()
            for avd_name, avd_data in config.items():
                if isinstance(avd_data, dict) and avd_data.get("authorized", False):
                    avd_data["authorized"] = False
            # Записываем изменения обратно в файл
            self._write_config(config)

    def reset_authorization(self, avd_name):
        """
        Сбрасываем статус авторизации эмулятора на False.
        Если эмулятор отсутствует в конфигурации, ничего не делаем.
        """
        with self.lock:
            config = self._read_config()
            if avd_name in config:
                logger.info(f"Статус эмулятора {avd_name} до сброса: {config.get(avd_name)}")
                config[avd_name]["authorized"] = False
                self._write_config(config)

    def was_started(self, avd_name):
        """Проверяем, был ли ранее запущен эмулятор (прогрузился ли он до рабочего стола)."""
        with self.lock:
            config = self._read_config()
        return avd_name in config

    def mark_as_started(self, avd_name):
        """Помечаем эмулятор как хотя бы один раз прогрузившийся до рабочего стола."""
        with self.lock:
            config = self._read_config()
            if avd_name not in config:
                config[avd_name] = {"authorized": False}
            self._write_config(config)

    def clear_emulator_data(self, avd_name):
        """Удаляет данные о конкретном эмуляторе из файла конфигурации."""
        with self.lock:
            config = self._read_config()
            if avd_name in config:
                del config[avd_name]
            self._write_config(config)