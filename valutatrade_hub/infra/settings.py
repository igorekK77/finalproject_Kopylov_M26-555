import json
from typing import Any


class SettingsLoader:
    """Класс - единая точка конфигурации и/или доступа к данным."""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Инициализация класса с настройками и открытие файла с настройками"""
        self.config_path = "data/config.json"
        with open(self.config_path, "r", encoding="utf-8") as file:
            self._config = json.load(file)

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки по ключу."""
        return self._config.get(key, default)

    def reload(self):
        """Повторно загружаем файл с настройками"""
        with open(self.config_path, "r", encoding="utf-8") as file:
            self._config = json.load(file)