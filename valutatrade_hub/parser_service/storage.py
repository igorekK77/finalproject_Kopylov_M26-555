import json
import os
from pathlib import Path

from valutatrade_hub.core.utils import load_json, save_json
from valutatrade_hub.parser_service.config import ParserConfig


class RatesStorage:
    """Класс сохраняет полученные курсы валют"""
    def save_rates(self, new_data: dict):
        """Функция сохраняет курсы валют в rates.json"""
        old_data = load_json(ParserConfig.RATES_FILE_PATH)

        old_pairs = old_data.get("pairs", {})
        new_pairs = new_data.get("pairs", {})
        old_pairs.update(new_pairs)

        old_data["pairs"] = old_pairs
        if new_pairs:
            old_data["last_refresh"] = new_data["last_refresh"]

        save_json(ParserConfig.RATES_FILE_PATH, old_data)

    def save_history(self, new_data: list[dict]):
        """Функция сохраняет курсы валют в exchange_rates.json"""
        filepath = Path(ParserConfig.HISTORY_FILE_PATH)
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as file:
                history = json.load(file)
        else:
            history = []
        existing_ids = {r["id"] for r in history}

        for rate in new_data:
            if rate["id"] not in existing_ids:
                history.append(rate)
                existing_ids.add(rate["id"])

        temp_filepath = filepath.with_name(filepath.name + ".tmp")
        with open(temp_filepath, "w", encoding="utf-8") as file:
            json.dump(history, file, indent=4, ensure_ascii=False)

        os.replace(temp_filepath, filepath)