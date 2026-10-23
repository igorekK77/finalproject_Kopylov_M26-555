import shlex
from tornado.options import print_help
from valutatrade_hub.core.usecases import register_user, login_user, show_portfolio, buy, sell, get_rate
from valutatrade_hub.decorators import handle_cli_errors


def interface():
    """Запускает CLI и обрабатывает пользовательский ввод."""
    print_help()
    login_access_user_id = None
    while True:
        user_input = input("Введите команду: ").strip()
        try:
            args = shlex.split(user_input)
        except ValueError as e:
            print(f"Ошибка: {e}")
            continue
        if not args:
            continue

        result = process_command(args, login_access_user_id)

        if result is None:
            continue
        login_access_user_id, should_exit = result
        if should_exit:
            return



@handle_cli_errors
def process_command(args: list[str], login_access_user_id: int | None):
    """Выполняет пользовательскую команду CLI."""
    command = args[0]
    match command:
        case "register":
            if len(args) > 3:
                if args[1] != "--username" or args[3] != "--password":
                    raise ValueError("Указаны неправильные аргументы")
            username = args[2] if len(args) > 2 else None
            password = args[4] if len(args) > 4 else None
            if username is None or password is None:
                raise ValueError("username или пароль указаны неправильно или не указаны."
                                 "Вызовите команду 'help' для просмотра правильного "
                                 "синтаксиса команды")
            message = register_user(username, password)
            print(message)
        case "login":
            if len(args) > 3:
                if args[1] != "--username" or args[3] != "--password":
                    raise ValueError("Указаны неправильные аргументы")
            username = args[2] if len(args) > 2 else None
            password = args[4] if len(args) > 4 else None
            if username is None or password is None:
                raise ValueError("username или пароль указаны неправильно или не указаны."
                                 "Вызовите команду 'help' для просмотра правильного "
                                 "синтаксиса команды")
            login_access_user_id = login_user(username, password)
            if login_access_user_id is None:
                print("Проверьте логин или пароль и авторизируйтесь снова")
                return None, False
            print(f"Вы вошли как '{username}'")
        case "show-portfolio":
            if login_access_user_id is None:
                raise ValueError("Для работы с этой функцие необходимо авторизироваться "
                                 "с помощью команды 'login' или зарегистрироваться")
            base = args[2] if len(args) > 2 else "USD"
            if len(args) > 2 and args[1] != "--base":
                raise ValueError("Указан неправильный аргумент")
            portfolio, total, username, total_base = show_portfolio(login_access_user_id, base)
            print(f"Портфель пользователя '{username}' (база: {total_base})")
            for key, value in portfolio.items():
                balance = value["balance"]
                result = value["result"]
                print(f"- {key}: {balance} -> {result} {total_base}")
            print("-" * 40)
            print(f"ИТОГО: {total} {total_base}")
        case "buy":
            if login_access_user_id is None:
                raise ValueError("Для работы с этой функцие необходимо авторизироваться "
                                 "с помощью команды 'login' или зарегистрироваться")
            if len(args) > 3:
                if args[1] != "--currency" or args[3] != "--amount":
                    raise ValueError("Указаны неправильные аргументы")
            currency = args[2] if len(args) > 2 else None
            amount = float(args[4]) if len(args) > 4 else None
            if currency is None or amount is None:
                raise ValueError("currency или amount указаны неправильно или не указаны."
                                 "Вызовите команду 'help' для просмотра правильного "
                                 "синтаксиса команды")
            result_buy = buy(currency, amount, login_access_user_id)
            print(f"Покупка выполнена: {result_buy["amount"]} "
                  f"{result_buy["currency"]} по курсу "
                  f"{result_buy["rate"]} USD/{result_buy["currency"]}")
            print("Изменения в портфеле:")
            print(f"- {result_buy["currency"]}: было {result_buy["old_balance"]} -> "
                  f"стало {result_buy["new_balance"]}")
            print(f"Оценочная стоимость покупки: {result_buy["sum_buy"]} USD")
        case "sell":
            if login_access_user_id is None:
                raise ValueError("Для работы с этой функцие необходимо авторизироваться "
                                 "с помощью команды 'login' или зарегистрироваться")
            if len(args) > 3:
                if args[1] != "--currency" or args[3] != "--amount":
                    raise ValueError("Указаны неправильные аргументы")
            currency = args[2] if len(args) > 2 else None
            amount = float(args[4]) if len(args) > 4 else None
            if currency is None or amount is None:
                raise ValueError("currency или amount указаны неправильно или не указаны."
                                 "Вызовите команду 'help' для просмотра правильного "
                                 "синтаксиса команды")
            result_sell = sell(currency, amount, login_access_user_id)
            print(
                f"Продажа выполнена: {result_sell['amount']} "
                f"{result_sell['currency']} по курсу "
                f"{result_sell['rate']} USD/{result_sell['currency']}"
            )
            print("Изменения в портфеле:")
            print(f"- {result_sell["currency"]}: было {result_sell["old_balance"]} "
                  f"-> стало {result_sell["new_balance"]}")
            print(f"Оценочная выручка: {result_sell["profit"]} USD")
        case "get-rate":
            if login_access_user_id is None:
                raise ValueError("Для работы с этой функцие необходимо авторизироваться "
                                 "с помощью команды 'login' или зарегистрироваться")
            if len(args) > 3:
                if args[1] != "--from" or args[3] != "--to":
                    raise ValueError("Указаны неправильные аргументы")
            from_currency = args[2] if len(args) > 2 else None
            to_currency = args[4] if len(args) > 4 else None
            if from_currency is None or to_currency is None:
                raise ValueError("currency или amount указаны неправильно или не указаны."
                                 "Вызовите команду 'help' для просмотра правильного "
                                 "синтаксиса команды")
            result_get_rate = get_rate(from_currency, to_currency)
            print(f"Курс {result_get_rate["from_currency"]}->{result_get_rate["to_currency"]}"
                  f": {result_get_rate["course_to_currency"]} (обновлено: "
                  f"{result_get_rate["update_time_rate"]})")
            print(f"Обратный курс {result_get_rate["to_currency"]}->"
                  f"{result_get_rate["from_currency"]}: "
                  f"{result_get_rate["course_from_currency"]}")
        case "help":
            print_help()
        case "exit":
            return login_access_user_id, True
        case _:
            print("Неизвестная команда. Повторите ввод")

    return login_access_user_id, False



def print_help() -> None:
    """Выводит справочную информацию по командам приложения."""

    print("\n***Система управления валютным портфелем***")
    print("Доступные команды:")

    print("<command> register --username <имя> --password <пароль> - "
          "зарегистрировать нового пользователя.")

    print("<command> login --username <имя> --password <пароль> - "
          "войти в учётную запись.")

    print("<command> show-portfolio [--base <валюта>] - "
          "показать кошельки и общую стоимость портфеля "
          "(по умолчанию USD).")

    print("<command> buy --currency <валюта> --amount <количество> - "
          "купить указанное количество валюты.")

    print("<command> sell --currency <валюта> --amount <количество> - "
          "продать указанное количество валюты.")

    print("<command> get-rate --from <валюта> --to <валюта> - "
          "получить текущий курс одной валюты к другой.")

    print("\nОбщие команды:")

    print("<command> help - вывести справочную информацию.")
    print("<command> exit - выйти из программы.\n")