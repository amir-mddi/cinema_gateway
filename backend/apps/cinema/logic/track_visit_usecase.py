from django.core import signing
from backend.apps.cinema.adapters.tracked_link import parse_link
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository


class TrackVisitUsecase:
    def __init__(self, repo: CatalogRepository):
        self.repo = repo

    def _target(self, token: str):
        telegram_id, film_id, _kind, target_id = parse_link(token)
        user = self.repo.user(telegram_id)
        film = self.repo.film_by_pk(film_id)
        if not film:
            raise signing.BadSignature("Film unavailable")
        task = self.repo.instagram_by_pk(target_id)
        if not task or task.pk not in {x.pk for x in self.repo.instagram_tasks(film)}:
            raise signing.BadSignature("Profile unrelated")
        return user, film, task.url, {"instagram_task": task}

    def follow(self, token):
        user, film, url, target = self._target(token)
        self.repo.visit(user, film, **target)
        return url
