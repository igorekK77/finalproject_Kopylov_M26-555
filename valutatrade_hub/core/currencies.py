from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.models import CryptoCurrency, Currency, FiatCurrency

CURRENCY_REGISTRY = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Proof of Stake", 4.5e11),
}

def get_currency(code: str) -> Currency:
    """Функция для получения объекта Currency по коду валюты"""
    currency_class = CURRENCY_REGISTRY.get(code, None)
    if currency_class is None:
        raise CurrencyNotFoundError(code)
    return currency_class
