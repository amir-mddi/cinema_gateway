"""Diagnose the exact Telegram channel/user/bot combination, without bypassing the gate."""
from django.core.management.base import BaseCommand, CommandError

from backend.apps.cinema.adapters.telegram_api import TelegramAPI, TelegramError
from backend.apps.cinema.entities.policies import membership_ok
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository


class Command(BaseCommand):
    help = "Check bot admin permissions and user membership for one channel; never prints tokens."

    def add_arguments(self, parser):
        parser.add_argument("--bot", required=True, help="Registered BotAccount key, e.g. bot01")
        parser.add_argument("--channel", required=True, type=int, help="Numeric -100... channel chat ID")
        parser.add_argument("--user", required=True, type=int, help="Personal Telegram user ID")

    def handle(self, *args, **options):
        repo = CatalogRepository()
        bot = repo.bot(options["bot"])
        if bot is None:
            raise CommandError("No active BotAccount has that key")
        channel = repo.channel_by_chat_id(options["channel"])
        if channel is None:
            raise CommandError("Channel ID not registered in Django Admin; check the numeric chat ID")
        api = TelegramAPI(bot)
        try:
            me = api.call("getMe")
            self.stdout.write(f"Bot: @{me['username']} (configured @{bot.username})")
            if me["username"].lower() != bot.username.lower().lstrip("@"):
                raise CommandError("The bot token and BotAccount username do not match")
            try:
                bot_membership = api.member(channel.chat_id, me["id"])
            except TelegramError as exc:
                raise CommandError(f"Bot's channel membership could not be checked: {exc}") from exc
            bot_status = bot_membership.get("status", "unknown")
            self.stdout.write(f"Bot's channel status: {bot_status}")
            if bot_status not in {"creator", "administrator"}:
                self.stdout.write(self.style.WARNING(
                    "Add THIS bot as a channel administrator; bot access is needed for reliable checks."
                ))
            try:
                user_membership = api.member(channel.chat_id, options["user"])
            except TelegramError as exc:
                raise CommandError(f"User membership check failed (check bot admin rights/chat ID): {exc}") from exc
            user_status = user_membership.get("status", "unknown")
            self.stdout.write(f"User's channel status: {user_status}")
            self.stdout.write(f"Membership gate result: {'PASS' if membership_ok(user_membership) else 'NOT JOINED'}")
            if membership_ok(user_membership):
                self.stdout.write(self.style.SUCCESS("Channel membership is confirmed for this account."))
        finally:
            api.close()
