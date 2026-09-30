import os
import re

_KEY = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


def token_for(bot):
    """Keep secrets out of DB, admin, links, and logs."""
    if bot is None:
        from django.conf import settings
        token = settings.TELEGRAM_BOT_TOKEN
    else:
        if not _KEY.fullmatch(bot.key):
            raise ValueError("Invalid bot key")
        token = os.environ.get("BOT_TOKEN_" + bot.key.upper().replace("-", "_"), "").strip()
    if not token:
        raise RuntimeError("Telegram token is missing for the selected bot")
    return token
