from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from backend.apps.cinema.models import Delivery, DeliveredMessage, ProcessedUpdate


class DeliveryRepository:
    def create(self, user, film):
        return Delivery.objects.create(user=user, film=film, bot=film.bot)

    def record_message(self, delivery, chat_id, message_id, ttl_seconds):
        return DeliveredMessage.objects.create(delivery=delivery, bot=delivery.bot, chat_id=chat_id, message_id=message_id,
                                               expires_at=timezone.now() + timedelta(seconds=ttl_seconds))

    def finish(self, delivery, error: str = ""):
        delivery.complete = not bool(error)
        delivery.error = error[:300]
        delivery.save(update_fields=["complete", "error"])

    def recent_delivery(self, user, film, seconds=15):
        return Delivery.objects.filter(user=user, film=film, created_at__gte=timezone.now()-timedelta(seconds=seconds)).exists()

    def update_processed(self, bot, update_id):
        return ProcessedUpdate.objects.filter(bot=bot, update_id=update_id).exists()

    def begin_update(self, bot, update_id):
        _, created = ProcessedUpdate.objects.get_or_create(bot=bot, update_id=update_id)
        return created

    def due_messages(self, limit=50):
        now = timezone.now()
        return list(DeliveredMessage.objects.filter(deleted_at__isnull=True, expires_at__lte=now,
                        next_attempt_at__lte=now, attempts__lt=12).select_related("delivery__bot").order_by("expires_at")[:limit])

    @transaction.atomic
    def mark_deleted(self, pk):
        DeliveredMessage.objects.filter(pk=pk, deleted_at__isnull=True).update(deleted_at=timezone.now())

    @transaction.atomic
    def retry_later(self, pk, attempt):
        delay = min(3600, 2 ** min(attempt, 10))
        DeliveredMessage.objects.filter(pk=pk, deleted_at__isnull=True).update(
            attempts=attempt, next_attempt_at=timezone.now()+timedelta(seconds=delay))
