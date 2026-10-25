from valutatrade_hub.infra.settings import SettingsLoader

settings = SettingsLoader()

FILE_PATH_USERS = settings.get("users_file")
FILE_PATH_PORTFOLIOS = settings.get("portfolios_file")
FILE_PATH_RATES = settings.get("rates_file")

DEFAULT_EXCHANGE_RATES = {
    "USD_USD": {"rate": 1.0},
    "EUR_USD": {"rate": 1.0786},
    "RUB_USD": {"rate": 0.01016},
    "BTC_USD": {"rate": 59337.21},
    "ETH_USD": {"rate": 3720.00},
    "SOL_USD": {"rate": 145.00}
}