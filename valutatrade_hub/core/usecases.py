import hashlib
import secrets
from valutatrade_hub.core.constants import FILE_PATH_USERS, FILE_PATH_PORTFOLIOS, FILE_PATH_RATES, \
    DEFAULT_EXCHANGE_RATES
from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import InsufficientFundsError, CurrencyNotFoundError, ApiRequestError
from valutatrade_hub.core.models import User, Portfolio, Wallet
from valutatrade_hub.core.utils import load_json, save_json, load_portfolios, save_portfolios
from datetime import datetime, timedelta

from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.settings import SettingsLoader


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

def show_portfolio(user_id: int, base: str = base_currency) -> tuple[dict[str, dict[str, float]],
                                                             float, str, str]:
    """Функция показывает все кошельки и итоговую стоимость
    в базовой валюте"""
    portfolios = load_json(FILE_PATH_PORTFOLIOS)
    users = load_json(FILE_PATH_USERS)
    rates = load_json(FILE_PATH_RATES)

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
    rates = load_json(FILE_PATH_RATES)
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
    rates = load_json(FILE_PATH_RATES)
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
        raise ValueError("Значение кода валюты должно быть не пустым и в верхнем регистре")
    get_currency(from_currency)
    get_currency(to_currency)
    rates = load_json(FILE_PATH_RATES)
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

    age_usd = datetime.now() - update_at_usd
    age_currency = datetime.now() - update_at_currency
    ttl = timedelta(seconds=settings.get("rates_ttl_seconds", 300))

    if age_usd > ttl:
        if key_to_usd in DEFAULT_EXCHANGE_RATES:
            rate_to_usd["rate"] = DEFAULT_EXCHANGE_RATES[key_to_usd]["rate"]
            update_at_usd = datetime.now()
            rate_to_usd["updated_at"] = update_at_usd.isoformat()
        else:
            raise ApiRequestError("Невозможно получить свежий курс валют")
    if age_currency > ttl:
        if key_to_currency in DEFAULT_EXCHANGE_RATES:
            rate_to_currency["rate"] = DEFAULT_EXCHANGE_RATES[key_to_currency]["rate"]
            update_at_currency = datetime.now()
            rate_to_currency["updated_at"] = update_at_currency.isoformat()
        else:
            raise ApiRequestError("Невозможно получить свежий курс валют")

    course_to_currency = rate_to_usd["rate"] / rate_to_currency["rate"]
    course_from_currency = rate_to_currency["rate"] / rate_to_usd["rate"]
    save_json(FILE_PATH_RATES, rates)

    return {"course_to_currency": course_to_currency, "course_from_currency":
        course_from_currency, "update_time_rate":
        min(update_at_usd, update_at_currency).isoformat(),
        "from_currency": from_currency, "to_currency": to_currency}