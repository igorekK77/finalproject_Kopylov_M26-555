import json
from datetime import datetime

from valutatrade_hub.core.constants import FILE_PATH_PORTFOLIOS, FILE_PATH_USERS, FILE_PATH_RATES
from valutatrade_hub.core.models import Portfolio, Wallet, User


def load_json(filepath: str):
    """Загрузка данных из JSON файла"""
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)

def save_json(filepath: str, data) -> None:
    """Сохранение данных в JSON файл"""
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def load_portfolios() -> list[Portfolio]:
    """Функция превращает список JSON-объектов в список Python объектов Portfolio"""
    data = load_json(FILE_PATH_PORTFOLIOS)

    portfolios = []

    for item in data:
        wallets = {
            code: Wallet(code, wallet_data["balance"])
            for code, wallet_data in item["wallets"].items()
        }
        portfolio = Portfolio(item["user_id"], wallets)
        portfolios.append(portfolio)

    return portfolios

def load_users() -> list[User]:
    """Функция превращает список JSON-объектов в список Python объектов User"""
    data = load_json(FILE_PATH_USERS)

    users = []

    for item in data:
        user = User(
            item["user_id"],
            item["username"],
            item["hashed_password"],
            item["salt"],
            datetime.fromisoformat(item["registration_date"])
        )

        users.append(user)

    return users

def save_portfolios(portfolios: list[Portfolio]) -> None:
    """Функция сохраняет список объектов Portfolio в список JSON объектов"""
    data = []

    for portfolio in portfolios:
        wallets = {
            currency_code: {"balance": wallet.balance}
            for currency_code, wallet in portfolio.wallets.items()
        }

        data.append({
            "user_id": portfolio.user_id,
            "wallets": wallets
        })

    save_json(FILE_PATH_PORTFOLIOS, data)