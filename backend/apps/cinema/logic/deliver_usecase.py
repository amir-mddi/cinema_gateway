import logging
import time
from django.conf import settings
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository
from backend.apps.cinema.repositories.delivery_repository import DeliveryRepository

log = logging.getLogger(__name__)


class DeliverFilmUsecase:
    def __init__(self, repo: CatalogRepository, deliveries: DeliveryRepository, telegram):
        self.repo, self.deliveries, self.telegram = repo, deliveries, telegram

    def execute(self, user, film, chat_id: int) -> str:
        """Returns sent, busy, no_media or failed. Re-check gate in the caller immediately before this call."""
        if self.deliveries.recent_delivery(user, film):
            return "busy"
        assets = self.repo.media(film)
        if not assets:
            return "no_media"
        delivery = self.deliveries.create(user, film)
        try:
            for index, asset in enumerate(assets):
                if index:
                    time.sleep(1.05)  # avoid bursts into a private chat
                media = self.telegram.deliver(asset.source.source_chat_id, asset.source.source_message_id, chat_id)
                # Persist before the next send; the independent cleanup worker handles these rows.
                self.deliveries.record_message(delivery, chat_id, media["message_id"], settings.MEDIA_TTL_SECONDS)
            self.deliveries.finish(delivery)
            return "sent"
        except Exception as exc:
            log.exception("Delivery failed for film=%s user=%s", film.pk, user.pk)
            self.deliveries.finish(delivery, str(exc))
            return "failed"
