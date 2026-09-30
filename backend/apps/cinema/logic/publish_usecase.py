from django.core.exceptions import ValidationError
from backend.apps.cinema.adapters.telegram_api import TelegramAPI
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository
from backend.apps.cinema.vo.texts import t
from backend.apps.cinema.enums.bot_enums import ButtonStyle


class PublishFilmUsecase:
    def __init__(self, repo=None, api_factory=None):
        self.repo = repo or CatalogRepository()
        self.api_factory = api_factory or TelegramAPI

    def execute(self, film):
        if not film.bot_id or not film.channel_id:
            raise ValidationError("Assign bot and dedicated channel before publishing")
        central = self.repo.central_channel()
        if central is None:
            raise ValidationError("Create and activate one central channel before publishing")
        api = self.api_factory(film.bot)
        try:
            message = api.send_text(
                central.chat_id,
                t("fa", "publish_announcement", film=film.title, link=film.deep_link(),
                  channel=film.channel.join_url),
                keyboard=[[{"text": t("fa", "publish_button"), "url": film.deep_link(),
                           "style": ButtonStyle.SUCCESS}]],
            )
            return message
        finally:
            api.close()
