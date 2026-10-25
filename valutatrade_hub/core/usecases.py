import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from valutatrade_hub.core.constants import (
    FILE_PATH_PORTFOLIOS,
    FILE_PATH_RATES,
    FILE_PATH_USERS,
)
from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import (
    load_json,
    load_portfolios,
    save_json,
    save_portfolios,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.updater import RatesUpdater

settings = SettingsLoader()
base_currency = settings.get("default_base_currency")

def register_user(username: str, password: str) -> str:
    """Функция регистрирует пользователя и создаёт для него пустой портфель."""
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Username должна быть строкой и не может быть пустой")
    if not isinstance(password, str) or len(password) < 4:
        raise ValueError("Пароль должен быть строкой длиной минимум 4 символа")
    users = load_json(FILE_PATH_USERS)
    portfolios = load_json(FILE_PATH_PORTFOLIOS)

    for user in users:
        if user["username"] == username:
            raise ValueError(f"Имя пользователя '{username}' уже используется")

    new_user_id = max([user["user_id"] for user in users], default=0) + 1
    salt = secrets.token_hex(16)
    password_with_salt = password + salt
    hashed_password = (hashlib.sha256(password_with_salt.encode("utf-8"))
                                 .hexdigest())
    registration_date = datetime.now()
    user = User(new_user_id, username, hashed_password, salt, registration_date)
    user_data = {
        "user_id": user.user_id,
        "username": user.username,
        "hashed_password": user.hashed_password,
        "salt": user.salt,
        "registration_date": user.registration_date.isoformat()
    }
    users.append(user_data)
    save_json(FILE_PATH_USERS, users)

    portfolio = Portfolio(user.user_id, {}, user)
    portfolio_data = {
        "user_id": portfolio.user.user_id,
        "wallets": {}
    }
    portfolios.append(portfolio_data)
    save_json(FILE_PATH_PORTFOLIOS, portfolios)
    return (f"Пользователь '{username}' зарегистрирован (id={user.user_id}). "
            f"Войдите: login --username {username} --password ****")

def login_user(username: str, password: str) -> int:
    """Функция авторизирует пользователя в системе"""
    users = load_json(FILE_PATH_USERS)

    user = next((u for u in users if u["username"] == username), None)
    if user is None:
        raise ValueError(f"Пользователь '{username}' не найден")

    salt = user["salt"]
    password_with_salt = password + salt
    hashed_password = (hashlib.sha256(password_with_salt.encode("utf-8"))
                       .hexdigest())
    if hashed_password != user["hashed_password"]:
        raise ValueError("Неверный пароль")
    return user["user_id"]

def show_portfolio(user_id: int, base: str = base_currency) -> tuple[dict[str,
                                                            dict[str, float]],
                                                             float, str, str]:
    """Функция показывает все кошельки и итоговую стоимость
    в базовой валюте"""
    portfolios = load_json(FILE_PATH_PORTFOLIOS)
    users = load_json(FILE_PATH_USERS)
    rates = load_json(FILE_PATH_RATES)["pairs"]

    user_portfolio = next((portfolio for portfolio in portfolios
                           if portfolio["user_id"] == user_id), None)
    if user_portfolio is None:
        raise ValueError(f"Портфолио пользователя {user_id} не найдено")
    user = next((u for u in users if u["user_id"] == user_id), None)
    if user is None:
        raise ValueError(f"Пользователь с ID = {user_id} не найден")

    base = base.upper()
    base_key = f"{base}_USD"

    if base_key not in rates:
        raise ValueError(f"Неизвестная базовая валюта '{base}'")

    wallets = {
        currency_code: Wallet(currency_code, data["balance"])
        for currency_code, data in user_portfolio["wallets"].items()
    }
    portfolio = Portfolio(user_id, wallets)
    total = {}
    for currency_code, wallet in wallets.items():
        currency_key = f"{currency_code}_USD"
        if currency_key not in rates:
            raise ValueError(f"Неизвестная валюта '{currency_code}'")
        result = wallet.balance * rates[currency_key]["rate"] / rates[base_key]["rate"]
        total[currency_code] = {"balance": wallet.balance, "result": result}
    return total, portfolio.get_total_value(base, rates), user["username"], base

@log_action("BUY", True)
def buy(currency: str, amount: float, user_id: int) -> dict[str, float]:
    """Функция позволяет купить валюту"""
    if not isinstance(currency, str):
        raise TypeError("Значение кода валюты должно быть передано строкой")
    if not isinstance(amount, (int, float)):
        raise TypeError("Значение количество покупаемой валюты должно быть числом")
    if amount <= 0:
        raise ValueError(f"Значение amount = {amount} меньше нуля")
    rates = load_json(FILE_PATH_RATES)["pairs"]
    currency = currency.strip().upper()
    get_currency(currency)
    if currency == "USD":
        raise ValueError("Нельзя купить USD за USD")
    key = f"{currency}_USD"
    if key not in rates:
        raise ValueError(f"Валюта {currency} не найдена")

    portfolios = load_portfolios()
    user_portfolio = next((portfolio for portfolio in portfolios
                           if portfolio.user_id == user_id), None)
    if user_portfolio is None:
        raise ValueError(f"Портфель пользователя {user_id} не найден")
    wallets = user_portfolio.wallets

    if "USD" not in wallets:
        user_portfolio.add_currency("USD")
    if currency not in wallets:
        user_portfolio.add_currency(currency)

    sum_buy = amount * rates[key]["rate"]
    old_balance = user_portfolio.wallets[currency].balance
    if sum_buy > user_portfolio.wallets["USD"].balance:
        raise InsufficientFundsError(user_portfolio.wallets["USD"].balance,
                                     user_portfolio.wallets["USD"].currency_code,
                                     sum_buy)
    user_portfolio.wallets["USD"].withdraw(sum_buy)
    user_portfolio.wallets[currency].deposit(amount)
    new_balance = user_portfolio.wallets[currency].balance
    save_portfolios(portfolios)
    return {"rate": rates[key]["rate"], "sum_buy": sum_buy, "old_balance": old_balance,
            "new_balance": new_balance, "amount": amount, "currency": currency}

@log_action("SELL", True)
def sell(currency: str, amount: float, user_id: int) -> dict[str, float]:
    """Функция позволяет продать указанную валюту."""
    if not isinstance(currency, str):
        raise TypeError("Значение кода валюты должно быть передано строкой")
    if not isinstance(amount, (float, int)):
        raise TypeError("Значение количество продаваемой валюты должно быть числом")
    if amount <= 0:
        raise ValueError(f"Значение amount = {amount} меньше нуля")
    currency = currency.strip().upper()
    if currency == "USD":
        raise ValueError("Нельзя продать USD за USD")
    get_currency(currency)
    rates = load_json(FILE_PATH_RATES)["pairs"]
    portfolios = load_portfolios()
    user_portfolio = next((portfolio for portfolio in portfolios if
                           portfolio.user_id == user_id), None)
    if user_portfolio is None:
        raise ValueError(f"Портфель пользователя {user_id} не найден")

    wallet_currency = user_portfolio.wallets.get(currency, None)
    if wallet_currency is None:
        raise ValueError(f"Кошелька для валюты {currency} не существует")
    old_balance = wallet_currency.balance
    if amount > wallet_currency.balance:
        raise InsufficientFundsError(wallet_currency.balance,
                                     wallet_currency.currency_code,
                                     amount)
    key = f"{currency}_USD"
    if key not in rates:
        raise ValueError(f"Курс для валюты {currency} не найден")
    rate = rates[key]["rate"]
    if rate is None:
        raise ValueError(f"Курс для валюты {currency} не найден")
    wallet_usd = user_portfolio.wallets.get("USD", None)
    if wallet_usd is None:
        user_portfolio.add_currency("USD")
        wallet_usd = user_portfolio.get_wallet("USD")
    wallet_currency.withdraw(amount)
    new_balance = wallet_currency.balance
    profit = rate * amount
    wallet_usd.deposit(profit)
    save_portfolios(portfolios)
    return {"old_balance": old_balance, "new_balance": new_balance,
            "profit": profit, "rate": rate, "currency": currency,
            "amount": amount}

def get_rate(from_currency: str, to_currency: str):
    """Функция позволяет получить текущий курс одной валюты к другой."""
    if not isinstance(from_currency, str) or not isinstance(to_currency, str):
        raise TypeError("Значение кода валюты должно быть передано строкой")
    if not from_currency.isupper() or not to_currency.isupper():
        raise ValueError("Значение кода валюты должно быть не пустым и "
                         "в верхнем регистре")
    get_currency(from_currency)
    get_currency(to_currency)
    rates = load_json(FILE_PATH_RATES)["pairs"]
    key_to_usd = f"{from_currency}_USD"
    key_to_currency = f"{to_currency}_USD"
    if key_to_usd not in rates:
        raise CurrencyNotFoundError(from_currency)
    if key_to_currency not in rates:
        raise CurrencyNotFoundError(to_currency)
    rate_to_usd = rates[key_to_usd]
    rate_to_currency = rates[key_to_currency]
    if rate_to_usd is None or rate_to_currency is None:
        raise ValueError(f"Невозможно перевести из валюты {from_currency} в "
                         f"валюту {to_currency}")
    date_time_usd = rate_to_usd["updated_at"]
    date_time_currency = rate_to_currency["updated_at"]

    update_at_usd = datetime.fromisoformat(date_time_usd)
    update_at_currency = datetime.fromisoformat(date_time_currency)

    age_usd = datetime.now(timezone.utc) - update_at_usd
    age_currency = datetime.now(timezone.utc) - update_at_currency
    ttl = timedelta(seconds=settings.get("rates_ttl_seconds", 300))

    if age_usd > ttl or age_currency > ttl:
        try:
            RatesUpdater().run_update()
        except Exception as e:
            raise ApiRequestError("Не удалось обновить курсы валют") from e
        rates = load_json(FILE_PATH_RATES)["pairs"]

        rate_to_usd = rates.get(key_to_usd)
        rate_to_currency = rates.get(key_to_currency)

        if rate_to_usd is None or rate_to_currency is None:
            raise ApiRequestError("Не удалось получить свежие курсы валют")

        update_at_usd = datetime.fromisoformat(rate_to_usd["updated_at"])
        update_at_currency = datetime.fromisoformat(rate_to_currency["updated_at"])

        now = datetime.now(timezone.utc)

        if (now - update_at_usd > ttl or
                now - update_at_currency > ttl):
            raise ApiRequestError("Не удалось обновить устаревшие курсы валют")

    course_to_currency = rate_to_usd["rate"] / rate_to_currency["rate"]
    course_from_currency = rate_to_currency["rate"] / rate_to_usd["rate"]

    return {"course_to_currency": course_to_currency, "course_from_currency":
        course_from_currency, "update_time_rate":
        min(update_at_usd, update_at_currency).isoformat(),
        "from_currency": from_currency, "to_currency": to_currency}


def show_rates(currency: str | None = None, top: int | None = None,
               base: str = "USD"):
    """Функция возвращает список актуальных курсов из
    локального кеша с возможностью фильтрации."""
    rates = load_json(FILE_PATH_RATES)["pairs"]
    if not rates:
        raise ValueError("Не удалось загрузить курсы валют")

    if base == "USD":
        base_rate = 1.0
    else:
        base_key = f"{base}_USD"
        if base_key not in rates:
            raise ValueError(f"Курс базовой валюты {base} не найден")
        base_rate = rates[base_key]["rate"]
        if base_rate <= 0:
            raise ValueError("Курс базовой валюты должен быть положительным")

    converted_rates = {}
    if base != "USD":
        for key, value in rates.items():
            from_currency = key.split("_")[0]
            if from_currency == base:
                continue

            new_key = f"{from_currency}_{base}"
            new_rate = value["rate"] / base_rate

            converted_rates[new_key] = {
                "rate": new_rate,
                "updated_at": value["updated_at"],
                "source": value["source"]
            }
    else:
        converted_rates = rates

    if currency is None and top is None:
        return converted_rates

    if currency is not None:
        key = f"{currency}_{base}"
        if key in converted_rates:
            return {key: converted_rates[key]}
        else:
            raise ValueError(f"Курса для валюты {currency} не найден")

    if top is not None:
        if top <= 0:
            raise ValueError("Значение top должно быть положительным")
        crypto_rates = {key: value for key, value in converted_rates.items()
                        if key.split("_")[0] in ParserConfig.CRYPTO_ID_MAP}
        sorted_rates = dict(sorted(crypto_rates.items(),
                                   key=lambda x: x[1]["rate"],
                                   reverse=True))
        if top > len(sorted_rates):
            raise ValueError(f"Указанное значение top = {top} больше, чем курсов валют")
        if len(sorted_rates) == top:
            return sorted_rates
        top_rates = {}
        counter = 0
        for key, value in sorted_rates.items():
            if counter == top:
                return top_rates
            top_rates[key] = value
            counter += 1
    raise ValueError("Не удалось вывести курсы валют")




