"""A signed Instagram-link click counts as opening the link, not actual follow."""
from django.core import signing
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed, HttpResponseRedirect
from django.views.decorators.cache import never_cache
from backend.apps.cinema.logic.track_visit_usecase import TrackVisitUsecase
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository
from backend.apps.cinema.vo.texts import t


@never_cache
def tracked_redirect(request, token: str):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    try:
        destination = TrackVisitUsecase(CatalogRepository()).follow(token)
        return HttpResponseRedirect(destination)
    except (signing.BadSignature, ValueError):
        return HttpResponseBadRequest(t("fa", "visit_expired"))
