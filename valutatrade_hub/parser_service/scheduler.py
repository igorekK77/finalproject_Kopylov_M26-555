import logging
import time

from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.updater import RatesUpdater


def run_scheduler():
    settings = SettingsLoader()
    ttl = settings.get("rates_ttl_seconds", 300)
    logger = logging.getLogger("valutatrade_hub")
    updater = RatesUpdater()

    while True:
        try:
            updater.run_update()
        except Exception:
            logger.exception("Ошибка при обновлении курсов")
        time.sleep(ttl)

if __name__ == "__main__":
    run_scheduler()
