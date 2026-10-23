from valutatrade_hub.core.utils import load_json
from valutatrade_hub.infra.settings import SettingsLoader


settings = SettingsLoader()

class ParserConfig:
    """Класс с основными параметрами для работы Parser Service"""
    secret_file = load_json("secret.json")

    EXCHANGERATE_API_KEY: str = secret_file["EXCHANGERATE_API_KEY"]
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Списки валют
    BASE_CURRENCY: str = settings.get("default_base_currency", "USD")
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    }

    # Пути
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    # Сетевые параметры
    REQUEST_TIMEOUT: int = 10