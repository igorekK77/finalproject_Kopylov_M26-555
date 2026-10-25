from functools import wraps

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.logging_config import setup_logging

logger = setup_logging()

def handle_cli_errors(func):
    """Перехватывает ошибки и выводит сообщения об этом пользователю."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InsufficientFundsError as e:
            print(e)
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            print("Проверьте код валюты. Примеры: USD, RUB, EUR, ETH, BTC")
        except ApiRequestError as e:
            print(f"Повторите попытку позже или проверьте соединение с интернетом\n"
                  f"{e}")
        except (ValueError, TypeError) as e:
            print(f"Ошибка: {e}")

    return wrapper

def log_action(action: str, verbose: bool = False):
    """Логирует ключевые операции"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            currency = kwargs.get("currency_code", args[0] if len(args) > 0 else None)
            amount = kwargs.get("amount", args[1] if len(args) > 1 else None)
            user_id = kwargs.get("user_id", args[2] if len(args) > 2 else None)
            try:
                result = func(*args, **kwargs)
                message = (
                    f"{action} user_id='{user_id}' "
                    f"currency='{currency}' "
                    f"amount={amount:.4f} "
                    f"rate={result["rate"]:.2f} "
                    f"base='USD' result=OK"
                )

                if verbose:
                    message += (
                        f" balance_before={result["old_balance"]} "
                        f"balance_after={result["new_balance"]}"
                    )

                logger.info(message)
                return result
            except Exception as e:
                logger.error(
                    f"{action} user_id='{user_id}' currency='{currency}' "
                    f"amount={amount} result=ERROR "
                    f"error_type='{type(e).__name__}' error_message={e.args[0]}"
                )
                raise

        return wrapper

    return decorator





