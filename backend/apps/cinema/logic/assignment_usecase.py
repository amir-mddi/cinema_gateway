import secrets
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository
from backend.apps.cinema.adapters.bot_credentials import token_for


class AssignFilmBotUsecase:
    def __init__(self, repo=None):
        self.repo = repo or CatalogRepository()

    def choose(self):
        eligible = []
        for bot in self.repo.active_bots():
            try:
                token_for(bot)
            except RuntimeError:
                continue
            eligible.append(bot)
        if not eligible:
            raise ValueError("No active bot with an environment token is configured")
        return secrets.choice(eligible)
