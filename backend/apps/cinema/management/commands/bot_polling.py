import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections, connections
from backend.apps.cinema.adapters.telegram_api import TelegramAPI, TelegramError
from backend.apps.cinema.controllers.update_controller import UpdateController
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository
from backend.apps.cinema.repositories.delivery_repository import DeliveryRepository
from backend.apps.cinema.vo.commands import set_commands

log = logging.getLogger(__name__)


def poll_bot(key):
    """One dedicated getUpdates stream per token; independently persisted update IDs."""
    close_old_connections()
    repo = CatalogRepository()
    bot = repo.bot(key) if key else None
    if key and bot is None:
        raise CommandError("Bot key is not registered or active")
    api = TelegramAPI(bot)
    controller = UpdateController(api, repository=repo, bot=bot)
    deliveries = DeliveryRepository()
    offset = 0
    try:
        me = api.call("getMe")
        if bot and me.get("username", "").lower() != bot.username.lower().lstrip("@"):
            raise CommandError(f"Bot username mismatch for key {key}")
        try:
            set_commands(api)
        except TelegramError:
            log.warning("Command registration failed for bot=%s", key)
        while True:
            try:
                updates = api.updates(offset)
                for update in updates:
                    update_id = update["update_id"]
                    if not deliveries.update_processed(bot, update_id):
                        try:
                            controller.process(update)
                            deliveries.begin_update(bot, update_id)
                        except Exception:
                            log.exception("Update handling failed for bot=%s update=%s", key, update_id)
                            raise
                    offset = update_id + 1
                close_old_connections()
            except TelegramError as exc:
                log.warning("Poll failed bot=%s: %s", key, exc)
                time.sleep(min(60, exc.retry_after or 3))
            except Exception:
                log.exception("Poll loop error bot=%s", key)
                close_old_connections()
                time.sleep(3)
    finally:
        api.close()
        connections.close_all()


def supervise_bot(key):
    """Restart a failed individual poller without stopping other bots."""
    while True:
        try:
            poll_bot(key)
        except Exception:
            log.exception("Bot worker stopped; retrying bot=%s in 30 seconds", key)
            time.sleep(30)


class Command(BaseCommand):
    help = "Poll --bot KEY, or --all active bot accounts (one concurrent stream per token)."

    def add_arguments(self, parser):
        parser.add_argument("--bot", default=None, help="BotAccount.key")
        parser.add_argument("--all", action="store_true", help="Start every registered active bot")

    def handle(self, *args, **options):
        key, all_bots = options["bot"], options["all"]
        if key and all_bots:
            raise CommandError("Choose either --bot or --all")
        if all_bots:
            keys = CatalogRepository().bot_keys()
            if not keys:
                raise CommandError("Register BotAccount records in Django admin first")
            self.stdout.write(f"Starting {len(keys)} bot workers")
            with ThreadPoolExecutor(max_workers=len(keys), thread_name_prefix="cinema-bot") as pool:
                futures = [pool.submit(supervise_bot, k) for k in keys]
                for future in as_completed(futures):
                    future.result()
        else:
            self.stdout.write(f"Starting bot: {key or 'legacy'}")
            poll_bot(key)
