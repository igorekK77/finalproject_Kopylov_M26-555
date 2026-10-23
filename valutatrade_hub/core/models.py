import hashlib
import secrets
from datetime import datetime
from abc import ABC, abstractmethod

from valutatrade_hub.core.constants import DEFAULT_EXCHANGE_RATES
from valutatrade_hub.core.exceptions import InsufficientFundsError


class User:
    """Класс, описывающий пользователя системы."""

    def __init__(self, user_id: int, username: str,
                 hashed_password: str, salt: str,
                 registration_date: datetime):
        """Функция, инициализирующая пользователя с указанными данными."""
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    def get_user_info(self):
        """Функция выводит информацию о пользователе (без пароля)."""
        return (f"Пользователь c ID = {self._user_id}, имя = {self._username}, "
                f"дата регистрации {self._registration_date}")

    def change_password(self, new_password: str) -> None:
        """Функция изменяет пароль пользователя, с хешированием нового пароля."""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов.")
        self._salt = secrets.token_hex(16)
        password_with_salt = new_password + self._salt
        self._hashed_password = (hashlib.sha256(password_with_salt.encode("utf-8"))
                                 .hexdigest())

    def verify_password(self, password : str) -> bool:
        """Функция проверяет введённый пароль на совпадение."""
        password_with_salt = password + self._salt
        chek_hash_password = (hashlib.sha256(password_with_salt.encode("utf-8"))
                              .hexdigest())
        if chek_hash_password == self._hashed_password:
            return True
        else:
            return False

    @property
    def username(self) -> str:
        """Возвращается имя пользователя"""
        return self._username

    @username.setter
    def username(self, new_username: str) -> None:
        """Устанавливается новое имя пользователя"""
        if not isinstance(new_username, str) or not new_username.strip():
            raise ValueError("Имя не может быть пустым")
        self._username = new_username

    @property
    def user_id(self) -> int:
        """Возвращается ID пользователя"""
        return self._user_id

    @property
    def registration_date(self) -> datetime:
        """Возвращается дата регистарции пользователя"""
        return self._registration_date

    @property
    def salt(self) -> str:
        """Возвращается соль пароля"""
        return self._salt

    @property
    def hashed_password(self) -> str:
        """Возвращается хеш пароля"""
        return self._hashed_password



class Wallet:
    """Класс, описывающий кошелёк пользователя для одной конкретной валюты"""

    def __init__(self, currency_code: str, balance: float):
        """Функция, инициализирующая кошелёк пользователя для одной
        конкретной валюты"""
        self.currency_code = currency_code
        self._balance = balance

    def deposit(self, amount: float) -> None:
        """Функция, пополняющая баланс"""
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма пополнения баланса должна быть числом")
        if amount < 0:
            raise ValueError("Сумма пополнения баланса не может "
                             "быть отрицательной")
        self._balance += amount

    def withdraw(self, amount: float) -> None:
        """Функция для снятие средств (если баланс позволяет)."""
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма снятия с баланса должна быть числом")
        if amount < 0:
            raise ValueError("Сумма снятия с баланса не может "
                             "быть отрицательной")
        if amount <= self._balance:
            self._balance -= amount
        else:
            raise InsufficientFundsError(self.balance, self.currency_code,
                                         amount)

    def get_balance_info(self) -> str:
        """Функция вывод информации о текущем балансе."""
        return f"Текущий баланс = {self._balance} {self.currency_code}"

    @property
    def balance(self) -> float:
        """Возвращает текущее значение баланса"""
        return self._balance

    @balance.setter
    def balance(self, amount: float) -> None:
        """Устанавливает новое значение баланса"""
        if not isinstance(amount, float):
            raise TypeError("Баланс должен быть числом с плавающей точкой")
        if amount < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = amount


class Portfolio:
    """Класс управление всеми кошельками одного пользователя"""

    def __init__(self, user_id: int, wallets: dict[str, Wallet], user: User | None = None):
        """Инициализация класса управления всеми кошельками одного пользователя"""
        self._user_id = user_id
        self._wallets = wallets
        self._user = user

    def add_currency(self, currency_code: str) -> None:
        """Функция добавляет новый кошелёк в портфель (если его ещё нет)."""
        if currency_code in self._wallets:
            raise ValueError(f"Кошелек для валюты с кодом {currency_code} уже создан")
        self._wallets[currency_code] = Wallet(currency_code, 0.0)

    def get_total_value(self, base_currency='USD', exchange_rates : dict[str, float]
                                                                    | None = None) -> float:
        """Функция возвращает общую стоимость всех валют пользователя в указанной
        базовой валюте"""
        if exchange_rates is None:
            exchange_rates = DEFAULT_EXCHANGE_RATES

        total = 0
        base_key = f"{base_currency}_USD"
        if base_key not in exchange_rates:
            raise ValueError(f"Неизвестная базовая валюта {base_currency}")
        for currency_code, wallet in self._wallets.items():
            key = f"{currency_code}_USD"
            if key not in exchange_rates:
                raise ValueError(f"Неизвестная валюта {currency_code}")
            sum_in_usd = wallet.balance * exchange_rates[key]["rate"]
            sum_in_base_currency = sum_in_usd / exchange_rates[base_key]["rate"]
            total += sum_in_base_currency

        return total

    def get_wallet(self, currency_code: str) -> Wallet:
        """Функция возвращает объект Wallet по коду валюты."""
        if currency_code not in self._wallets:
            raise ValueError(f"Кошелька с кодом валюты {currency_code} нету")
        return self._wallets[currency_code]

    @property
    def user(self) -> User | None:
        """Возвращает объект пользователя"""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Возвращает копию словаря кошельков."""
        return self._wallets.copy()

    @property
    def user_id(self):
        """Возвращает ID пользователя"""
        return self._user_id


class Currency(ABC):
    """Абстрактный базовый класс для валют"""
    def __init__(self, name: str, code: str):
        """Инициализация абстрактного базового класса"""
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Имя name = {name} не может быть пустым")
        if (not isinstance(code, str) or not 2 <= len(code) <= 5 or not code.isupper()
                or " " in code):
            raise ValueError(f"{code} должен быть в верхнем регистре, 2–5 символов, без пробелов.")
        self.name = name
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Функция возвращает строковое представление валюты"""
        pass

class FiatCurrency(Currency):
    """Класс-наследник Currency для обычных валют"""
    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        """Инициализация класса-наследника FiatCurrency"""
        super().__init__(name, code)
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return (f"Fiat: \"[FIAT] {self.code} — {self.name} ("
                f"Issuing: {self.issuing_country})\"")

class CryptoCurrency(Currency):
    """Класс-наследник Currency для криптовалют"""
    def __init__(self, name: str, code: str, algorithm: str, market_cap: float) -> None:
        """Инициализация класса-наследника CryptoCurrency"""
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        return (f"Crypto: \"[CRYPTO] {self.code} — {self.name} "
                f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})\"")
