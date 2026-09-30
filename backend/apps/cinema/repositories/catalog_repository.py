from django.db.models import Q
from backend.apps.cinema.models import BotAccount, BotUser, Channel, Film, InstagramTask, MediaSource, FilmAsset, LinkVisit


class CatalogRepository:
    def user(self, telegram_id: int) -> BotUser:
        user, _ = BotUser.objects.get_or_create(telegram_id=telegram_id)
        return user

    def bot(self, key):
        return BotAccount.objects.filter(key=key, active=True).first()

    def bot_keys(self):
        return list(BotAccount.objects.filter(active=True).order_by("pk").values_list("key", flat=True))

    def active_bots(self):
        return list(BotAccount.objects.filter(active=True).order_by("pk"))

    def film(self, slug: str, bot=None) -> Film | None:
        query = Film.objects.filter(slug=slug, active=True).select_related("bot", "channel")
        if bot is not None:
            query = query.filter(bot=bot)
        else:
            query = query.filter(bot__isnull=True)  # legacy single-bot mode only
        return query.first()

    def films(self, offset: int = 0, limit: int = 8, bot=None):
        query = Film.objects.filter(active=True)
        query = query.filter(bot=bot) if bot is not None else query.filter(bot__isnull=True)
        return list(query.order_by("title", "pk")[offset:offset + limit])

    def central_channel(self):
        return Channel.objects.filter(is_central=True, active=True).first()

    def channel_by_chat_id(self, chat_id: int):
        return Channel.objects.filter(chat_id=chat_id, active=True).first()

    def required_channels(self, film: Film):
        ids = set(film.required_channels.filter(active=True).values_list("pk", flat=True))
        central = self.central_channel()
        if central:
            ids.add(central.pk)
        if film.channel_id and film.channel.active:
            ids.add(film.channel_id)
        return list(Channel.objects.filter(pk__in=ids, active=True).order_by("pk"))

    def instagram_tasks(self, film: Film):
        return list(InstagramTask.objects.filter(active=True).filter(
            Q(films=film) | Q(films__isnull=True)
        ).distinct().order_by("pk"))

    def has_visit(self, user: BotUser, film: Film, *, post=None, instagram_task=None) -> bool:
        return LinkVisit.objects.filter(user=user, film=film, post=post, instagram_task=instagram_task).exists()

    def visit(self, user: BotUser, film: Film, *, post=None, instagram_task=None):
        LinkVisit.objects.get_or_create(user=user, film=film, post=post, instagram_task=instagram_task)

    def media(self, film: Film):
        return list(FilmAsset.objects.filter(film=film).select_related("source").order_by("position", "pk"))

    def save_last_film(self, user: BotUser, film: Film):
        if user.last_film_id != film.pk:
            user.last_film = film
            user.save(update_fields=["last_film"])

    def language(self, user: BotUser, language: str):
        user.language = language
        user.save(update_fields=["language"])

    def record_media(self, chat_id: int, message_id: int, media_type: str, caption: str, bot=None):
        return MediaSource.objects.get_or_create(bot=bot, source_chat_id=chat_id, source_message_id=message_id,
                                                 defaults={"media_type": media_type,
                                                           "caption": caption[:240]})

    def film_by_pk(self, film_id: int):
        return Film.objects.filter(pk=film_id, active=True).first()

    def instagram_by_pk(self, task_id: int):
        return InstagramTask.objects.filter(pk=task_id, active=True).first()

    def is_film_channel_for_bot(self, chat_id: int, bot) -> bool:
        return Film.objects.filter(channel__chat_id=chat_id, bot=bot, active=True).exists()

