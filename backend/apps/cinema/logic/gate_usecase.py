"""Evaluate only actionable, outstanding prerequisites for one film."""
import logging
from dataclasses import dataclass

from backend.apps.cinema.adapters.tracked_link import make_link
from backend.apps.cinema.entities.policies import RequirementResult, membership_ok
from backend.apps.cinema.enums.bot_enums import ClickKind
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository
from backend.apps.cinema.vo.texts import t

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class GateSnapshot:
    result: RequirementResult
    buttons: list[list[dict]]
    notice_key: str = "join_channels"


class GateUsecase:
    def __init__(self, repository: CatalogRepository, telegram):
        self.repo = repository
        self.telegram = telegram

    def evaluate(self, user, film) -> GateSnapshot:
        """Never confuse API lookup failures with non-membership.

        Channel administrators/owners pass getChatMember's 'administrator'/'creator'
        statuses. Post visits are no longer a prerequisite, even for old channels
        whose legacy require_post_clicks flag remains true in the database.
        """
        lang = user.language
        pending, buttons = [], []
        setup_error = False
        lookup_error = False
        missing_channel = False
        missing_follow = False

        if film.bot_id and (not film.channel_id or not film.channel.active):
            setup_error = True
            pending.append(t(lang, "film_channel_unavailable"))
        if film.bot_id and self.repo.central_channel() is None:
            setup_error = True
            pending.append(t(lang, "central_channel_unavailable"))

        for channel in self.repo.required_channels(film):
            label = t(lang, "channel", name=channel.name)
            try:
                member_payload = self.telegram.member(channel.chat_id, user.telegram_id)
                if not isinstance(member_payload, dict) or "status" not in member_payload:
                    raise ValueError("Invalid getChatMember response")
                is_member = membership_ok(member_payload)
            except Exception:
                # Do not tell a channel owner/admin they are not a member if
                # the BOT lacks permissions, its chat ID is wrong, or API is down.
                log.exception("getChatMember failed channel_pk=%s chat_id=%s user_id=%s",
                              channel.pk, channel.chat_id, user.telegram_id)
                lookup_error = True
                pending.append(t(lang, "membership_unavailable", name=channel.name))
                continue
            if not is_member:
                missing_channel = True
                pending.append(label)
                buttons.append([{"text": label, "url": channel.join_url}])

        for task in self.repo.instagram_tasks(film):
            if not self.repo.has_visit(user, film, instagram_task=task):
                missing_follow = True
                label = t(lang, "instagram", name=task.name)
                pending.append(label)
                buttons.append([{"text": label, "url": make_link(
                    user.telegram_id, film.pk, ClickKind.INSTAGRAM, task.pk)}])

        if setup_error:
            notice_key = "setup_unavailable"
        elif lookup_error:
            notice_key = "membership_check_unavailable"
        elif missing_channel and missing_follow:
            notice_key = "join_and_follow"
        elif missing_channel:
            notice_key = "join_channels"
        elif missing_follow:
            notice_key = "follow_pages"
        else:
            notice_key = "ready"
        return GateSnapshot(
            result=RequirementResult(complete=not pending, missing=tuple(pending)),
            buttons=buttons, notice_key=notice_key,
        )
