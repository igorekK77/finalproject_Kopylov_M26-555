import json
from abc import ABC, abstractmethod

import requests
from requests import JSONDecodeError, RequestException

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Абстрактный базовый класс для работы с внешними сервисами"""
    @abstractmethod
    def fetch_rates(self) -> dict:
        pass

class CoinGeckoClient(BaseApiClient):
    """Класс для работы с сервисом CoinGecko"""

    def fetch_rates(self) -> dict:
        """Функция получает курсы криптовалют и обрабатывает их"""
        settings = SettingsLoader()
        url_for_request = (f"{ParserConfig.COINGECKO_URL}?ids="
                           f"{",".join(ParserConfig.CRYPTO_ID_MAP.values())}"
                           f"&vs_currencies={settings.get("default_base_currency",
                                                          "usd").lower()}")
        try:
            response = requests.get(url_for_request, timeout=10)
            if response.status_code != 200:
                raise ApiRequestError(f"Ошибка запроса: {response.status_code}")
            data = json.loads(response.text)
        except JSONDecodeError as e:
            raise ApiRequestError(f"Ошибка парсинга JSON: {e}") from e
        except RequestException as e:
            raise ApiRequestError(f"Ошибка соединения с CoinGecko: {e}") from e

        result = {}
        base_currency = settings.get("default_base_currency", "USD").upper()
        for key, value in data.items():
            code_currency = next((c for c, v in ParserConfig.CRYPTO_ID_MAP.items()
                                  if v == key), None)
            full_code_currency= f"{code_currency}_{base_currency}"
            price = value.get(base_currency.lower())
            if price is None:
                raise ApiRequestError(f"Курс {key} к {base_currency} отсутствует")
            result[full_code_currency] = price

        return result


class ExchangeRateApiClient(BaseApiClient):
    """Класс для работы с сервисом ExchangeRate"""
    def fetch_rates(self) -> dict:
        """Функция получает курсы валют и обрабатывает их"""
        settings = SettingsLoader()
        url_for_request = (f"{ParserConfig.EXCHANGERATE_API_URL}/"
                           f"{ParserConfig.EXCHANGERATE_API_KEY}/"
                           f"latest/{settings.get("default_base_currency",
                                                          "USD")}")

        try:
            response = requests.get(url_for_request, timeout=10)
            if response.status_code != 200:
                raise ApiRequestError(f"Ошибка запроса: {response.status_code}")
            all_data = json.loads(response.text)
            if all_data.get("result") == "error":
                error_type = all_data.get("error-type", "unknown")
                raise ApiRequestError(f"Ошибка ExchangeRate-API: {error_type}")
            data = all_data.get("conversion_rates", None)
            if not isinstance(data, dict):
                raise ApiRequestError("В ответе отсутствуют курсы валют")
        except JSONDecodeError as e:
            raise ApiRequestError(f"Ошибка парсинга JSON: {e}") from e
        except RequestException as e:
            raise ApiRequestError(f"Ошибка соединения с ExchangeRate: {e}") from e

        result = {}
        base_currency = settings.get("default_base_currency", "USD").upper()
        for key, value in data.items():
            if not isinstance(value, (int, float)) or value <= 0:
                raise ApiRequestError(f"Некорректный курс валюты {key}: {value}")

            result[f"{key}_{base_currency}"] = 1 / value

        return result