import logging
import httpx
from django.conf import settings

log = logging.getLogger(__name__)


class TelegramError(Exception):
    def __init__(self, description, status_code=None, retry_after=None):
        super().__init__(description)
        self.status_code = status_code
        self.retry_after = retry_after


class TelegramAPI:
    """The only layer that knows Telegram's HTTP API; httpx proxy supports http/https/socks5."""

    def __init__(self, bot=None):
        from backend.apps.cinema.adapters.bot_credentials import token_for
        self.base_url = f"https://api.telegram.org/bot{token_for(bot)}/"
        self.client = httpx.Client(proxy=settings.PROXY_URL, timeout=settings.BOT_REQUEST_TIMEOUT)

    def close(self):
        self.client.close()

    def call(self, method: str, **payload):
        try:
            response = self.client.post(self.base_url + method, json=payload)
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TelegramError(f"Telegram network/response error ({type(exc).__name__})") from exc
        if not data.get("ok"):
            params = data.get("parameters") or {}
            raise TelegramError(data.get("description", "Telegram API failed"), data.get("error_code"), params.get("retry_after"))
        return data["result"]

    def send_text(self, chat_id, text, keyboard=None):
        args = {"chat_id": chat_id, "text": text, "link_preview_options": {"is_disabled": True}}
        if keyboard is not None:
            args["reply_markup"] = {"inline_keyboard": keyboard}
        return self.call("sendMessage", **args)

    def edit_text(self, chat_id, message_id, text, keyboard=None):
        args = {"chat_id": chat_id, "message_id": message_id, "text": text,
                "link_preview_options": {"is_disabled": True}}
        if keyboard is not None:
            args["reply_markup"] = {"inline_keyboard": keyboard}
        try:
            return self.call("editMessageText", **args)
        except TelegramError as exc:
            if "message is not modified" in str(exc).lower():
                return None
            if "message to edit not found" in str(exc).lower() or "message can't be edited" in str(exc).lower():
                return self.send_text(chat_id, text, keyboard)
            raise

    def answer_callback(self, callback_id, text=""):
        try:
            return self.call("answerCallbackQuery", callback_query_id=callback_id, text=text[:200])
        except TelegramError:
            log.info("Callback expired")

    def member(self, channel_chat_id, user_id):
        return self.call("getChatMember", chat_id=channel_chat_id, user_id=user_id)

    def deliver(self, source_chat_id, source_message_id, destination_chat_id):
        method = "forwardMessage" if settings.DELIVERY_MODE == "forward" else "copyMessage"
        return self.call(method, from_chat_id=source_chat_id, message_id=source_message_id,
                         chat_id=destination_chat_id, protect_content=False)

    def delete(self, chat_id, message_id):
        return self.call("deleteMessage", chat_id=chat_id, message_id=message_id)

    def updates(self, offset):
        return self.call("getUpdates", offset=offset, timeout=25, limit=50,
                         allowed_updates=["message", "callback_query", "channel_post"])
