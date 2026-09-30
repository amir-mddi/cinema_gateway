import logging
import time
from django.core.management.base import BaseCommand
from backend.apps.cinema.adapters.telegram_api import TelegramAPI, TelegramError
from backend.apps.cinema.repositories.delivery_repository import DeliveryRepository

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete due messages via the bot that originally sent them (one worker per DB)."

    def handle(self, *args, **options):
        clients = {}
        repo = DeliveryRepository()
        self.stdout.write("Starting multi-bot expiration worker")
        try:
            while True:
                for item in repo.due_messages():
                    bot = item.delivery.bot
                    key = bot.key if bot else "__legacy__"
                    try:
                        if key not in clients:
                            clients[key] = TelegramAPI(bot)
                        clients[key].delete(item.chat_id, item.message_id)
                        repo.mark_deleted(item.pk)
                    except TelegramError as exc:
                        if "message to delete not found" in str(exc).lower():
                            repo.mark_deleted(item.pk)
                        else:
                            log.warning("Delete failed id=%s bot=%s: %s", item.pk, key, exc)
                            repo.retry_later(item.pk, item.attempts + 1)
                    except Exception:
                        log.exception("Deletion worker failed id=%s bot=%s", item.pk, key)
                        repo.retry_later(item.pk, item.attempts + 1)
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write("Stopping cleanup worker")
        finally:
            for client in clients.values():
                client.close()
