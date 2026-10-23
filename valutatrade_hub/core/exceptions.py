class CurrencyNotFoundError(Exception):
    """Исключение для неизвестной валюты"""
    def __init__(self, code: str):
        super().__init__(f"Валюта с кодом '{code}' не найдена")

class InsufficientFundsError(Exception):
    """Исключение для недостатка средств"""
    def __init__(self, available: float, code: str, required: float):
        super().__init__(f"Недостаточно средств: доступно {available} {code},"
                         f" требуется {required} {code}")

class ApiRequestError(Exception):
    """Исключение для сбоя внешнего API"""
    def __init__(self, reason: str):
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")