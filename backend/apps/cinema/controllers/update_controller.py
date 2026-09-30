import logging
from django.conf import settings
from backend.apps.cinema.dtos.events import UserEvent
from backend.apps.cinema.logic.conversation_usecase import ConversationUsecase
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository
from backend.apps.cinema.vo.texts import t


log = logging.getLogger(__name__)


class UpdateController:
    def __init__(self, telegram, repository=None, bot=None):
        self.bot = bot
        self.telegram = telegram
        self.repo = repository or CatalogRepository()
        self.conversation = ConversationUsecase(telegram, repo=self.repo, bot=self.bot)

    def process(self, update: dict):
        channel_post = update.get("channel_post")
        if channel_post:
            chat_id = channel_post["chat"]["id"]
            log.info("channel_post from chat_id=%s", chat_id)
            # Channel post-view tracking has been removed. Channel posts are
            # processed only when they are candidate media sources.
            if chat_id == settings.STORAGE_CHAT_ID or self.repo.is_film_channel_for_bot(chat_id, self.bot):
                self._save_media(channel_post, notify=False, shared=True)
            return

        query = update.get("callback_query")
        if query:
            user_id = query["from"]["id"]
            message = query.get("message") or {}
            chat = message.get("chat") or {}
            if chat.get("type") != "private" or chat.get("id") != user_id:
                self.telegram.answer_callback(query["id"])
                return
            data = query.get("data") or ""
            action, sep, argument = data.partition(":")
            self.conversation.execute(UserEvent(user_id, user_id, message.get("message_id"), query["id"], action, argument))
            return

        message = update.get("message")
        if not message or message.get("chat", {}).get("type") != "private":
            return
        user_id = message.get("from", {}).get("id")
        chat_id = message["chat"]["id"]
        if user_id != chat_id:
            return
        if any(k in message for k in ("video", "document", "animation")):
            if user_id in settings.ADMIN_TELEGRAM_IDS:
                self._save_media(message, notify=True, shared=False)
            return
        raw_text = (message.get("text") or "").strip()
        command, _, argument = raw_text.partition(" ")
        name = command.split("@", 1)[0].lower()
        action = {"/start": "start", "/menu": "menu", "/language": "language"}.get(name, "menu")
        self.conversation.execute(UserEvent(user_id, chat_id, None, None, action, argument.strip()))

    def _save_media(self, message, notify, shared=False):
        media_type = next((key for key in ("video", "document", "animation") if key in message), None)
        if not media_type:
            return
        chat_id = message["chat"]["id"]
        source, created = self.repo.record_media(chat_id, message["message_id"], media_type, message.get("caption", ""),
                                                 bot=None if shared else self.bot)
        if notify:
            lang = self.repo.user(chat_id).language
            self.telegram.send_text(chat_id, t(lang, "source_saved", chat_id=source.source_chat_id,
                                               message_id=source.source_message_id))
