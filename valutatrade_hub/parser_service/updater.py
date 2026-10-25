import logging
from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Класс координирует весь процесс обновления курсов валют"""
    def __init__(self):
        self.coin_gecko_client = CoinGeckoClient()
        self.exchange_rate_client = ExchangeRateApiClient()
        self.storage = RatesStorage()

    def run_update(self, source: str | None = None):
        """Получает данные от каждого клиента, обрабатывает их и сохраняет"""
        logger = logging.getLogger("valutatrade_hub")
        if source not in (None, "exchangerate", "coingecko"):
            raise ValueError(f"Неизвестный источник: {source}")
        logger.info("Начало обновления курсов")
        exchange_rate = {}
        coin_gecko = {}
        errors = []
        if source is None or source == "exchangerate":
            try:
                exchange_rate = self.exchange_rate_client.fetch_rates()
                logger.info(
                    f"ExchangeRate-API: получено {len(exchange_rate)} курсов"
                )
            except ApiRequestError as e:
                logger.error(f"Ошибка ExchangeRate-API: {e}")
                errors.append("exchangerate")
        if source is None or source == "coingecko":
            try:
                coin_gecko = self.coin_gecko_client.fetch_rates()
                logger.info(
                    f"CoinGecko: получено {len(coin_gecko)} курсов"
                )
            except ApiRequestError as e:
                logger.error(f"Ошибка CoinGecko: {e}")
                errors.append("coingecko")

        time_now = datetime.now(timezone.utc).isoformat()
        all_rates = {}
        all_exchange_rates = []

        for key, value in exchange_rate.items():
            all_rates[key] = {
                "rate": value,
                "updated_at": time_now,
                "source": "ExchangeRate-API"
            }

            currency = key.split("_")
            exchange_rates = {
                "id": f"{key}_{time_now}",
                "from_currency": currency[0],
                "to_currency": currency[1],
                "rate": value,
                "timestamp": time_now,
                "source": "ExchangeRate-API",
                "meta": {}
            }
            all_exchange_rates.append(exchange_rates)

        for key, value in coin_gecko.items():
            all_rates[key] = {
                "rate": value,
                "updated_at": time_now,
                "source": "CoinGecko"
            }

            currency = key.split("_")
            exchange_rates = {
                "id": f"{key}_{time_now}",
                "from_currency": currency[0],
                "to_currency": currency[1],
                "rate": value,
                "timestamp": time_now,
                "source": "CoinGecko",
                "meta": {
                    "raw_id": ParserConfig.CRYPTO_ID_MAP.get(currency[0])
                }
            }
            all_exchange_rates.append(exchange_rates)

        result = {
            "pairs": all_rates,
            "last_refresh": time_now
        }

        if all_rates:
            self.storage.save_rates(result)

        if all_exchange_rates:
            self.storage.save_history(all_exchange_rates)

        logger.info("Обновление курсов завершено")

        return {
            "success": len(errors) == 0,
            "total_updated": len(all_rates),
            "last_refresh": time_now if all_rates else None,
            "errors": errors
        }

