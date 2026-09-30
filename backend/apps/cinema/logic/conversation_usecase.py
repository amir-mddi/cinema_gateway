from django.conf import settings
from backend.apps.cinema.enums.bot_enums import Language
from backend.apps.cinema.logic.deliver_usecase import DeliverFilmUsecase
from backend.apps.cinema.logic.gate_usecase import GateUsecase
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository
from backend.apps.cinema.repositories.delivery_repository import DeliveryRepository
from backend.apps.cinema.services.keyboards import KeyboardFactory
from backend.apps.cinema.vo.callbacks import parse_start, valid_slug
from backend.apps.cinema.vo.texts import t


class ConversationUsecase:
    def __init__(self, telegram, repo=None, delivery_repo=None, bot=None):
        self.bot = bot
        self.telegram = telegram
        self.repo = repo or CatalogRepository()
        self.deliveries = delivery_repo or DeliveryRepository()
        self.keyboards = KeyboardFactory()
        self.gate = GateUsecase(self.repo, telegram)
        self.sender = DeliverFilmUsecase(self.repo, self.deliveries, telegram)

    def _display(self, event, text, buttons=None):
        if event.callback_id and event.message_id:
            self.telegram.edit_text(event.chat_id, event.message_id, text, buttons)
        else:
            self.telegram.send_text(event.chat_id, text, buttons)

    def _menu(self, event, user, offset=0):
        films = self.repo.films(offset=offset, bot=self.bot)
        self._display(event, t(user.language, "welcome") if films else t(user.language, "films_empty"),
                      self.keyboards.menu(user, films, offset))

    def _film(self, event, user, slug):
        if not valid_slug(slug):
            self._display(event, t(user.language, "missing"))
            return
        film = self.repo.film(slug, bot=self.bot)
        if not film:
            self._display(event, t(user.language, "missing"))
            return
        self.repo.save_last_film(user, film)
        snapshot = self.gate.evaluate(user, film)
        if snapshot.result.complete:
            if event.callback_id:
                self.telegram.answer_callback(event.callback_id)
            self._display(event, t(user.language, "ready"), self.keyboards.ready(user, film))
        else:
            if event.callback_id:
                self.telegram.answer_callback(event.callback_id, t(user.language, snapshot.notice_key))
            self._display(event, t(user.language, snapshot.notice_key),
                          self.keyboards.requirements(user, film, snapshot))

    def execute(self, event):
        user = self.repo.user(event.telegram_id)
        action = event.action
        if action == "start":
            slug = parse_start(event.argument)
            if slug:
                self._film(event, user, slug)
            elif event.argument:
                self._display(event, t(user.language, "missing"))
            else:
                self._menu(event, user)
        elif action == "menu":
            try:
                offset = int(event.argument or 0)
            except ValueError:
                offset = 0
            self._menu(event, user, max(0, min(offset, 10000)))
        elif action == "language":
            self._display(event, t(user.language, "language"), self.keyboards.language())
        elif action == "lang" and event.argument in (Language.FA, Language.EN):
            self.repo.language(user, event.argument)
            self._display(event, t(user.language, "lang_saved"), self.keyboards.menu(user, self.repo.films(bot=self.bot)))
        elif action in ("film", "check"):
            self._film(event, user, event.argument)
        elif action == "watch":
            film = self.repo.film(event.argument, bot=self.bot) if valid_slug(event.argument) else None
            if not film:
                self._display(event, t(user.language, "missing"))
                return
            # Gate is always checked again at delivery time, including membership.
            snapshot = self.gate.evaluate(user, film)
            if not snapshot.result.complete:
                self._film(event, user, film.slug)
                return
            if self.deliveries.recent_delivery(user, film):
                self._display(event, t(user.language, "too_many"), self.keyboards.ready(user, film))
                return
            if not self.repo.media(film):
                self._display(event, t(user.language, "no_media"), self.keyboards.ready(user, film))
                return
            self._display(event, t(user.language, "sending", seconds=settings.MEDIA_TTL_SECONDS))
            status = self.sender.execute(user, film, event.chat_id)
            key = {"sent": "sent", "busy": "too_many", "no_media": "no_media", "failed": "delivery_failed"}[status]
            self.telegram.send_text(event.chat_id, t(user.language, key, seconds=settings.MEDIA_TTL_SECONDS),
                                    self.keyboards.ready(user, film) if status != "sent" else
                                    [[{"text": t(user.language, "menu"), "callback_data": "menu:0"}]])
        else:
            self._menu(event, user)
