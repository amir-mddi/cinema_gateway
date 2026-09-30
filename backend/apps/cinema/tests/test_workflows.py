from urllib.parse import urlsplit
from unittest.mock import patch

from django.test import TestCase

from backend.apps.cinema.adapters.tracked_link import make_link
from backend.apps.cinema.dtos.events import UserEvent
from backend.apps.cinema.logic.conversation_usecase import ConversationUsecase
from backend.apps.cinema.logic.deliver_usecase import DeliverFilmUsecase
from backend.apps.cinema.logic.gate_usecase import GateUsecase
from backend.apps.cinema.models import (
    BotAccount, BotUser, Channel, ChannelPost, Film, FilmAsset, InstagramTask,
    LinkVisit, MediaSource, DeliveredMessage,
)
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository
from backend.apps.cinema.repositories.delivery_repository import DeliveryRepository


class FakeTelegram:
    status = "member"
    fail_membership = False

    def __init__(self):
        self.status_by_chat_id = {}
        self.edited = []
        self.sent = []

    def member(self, chat_id, user_id):
        if self.fail_membership:
            raise RuntimeError("getChatMember unavailable")
        return {"status": self.status_by_chat_id.get(chat_id, self.status)}

    def deliver(self, source_chat_id, source_message_id, destination_chat_id):
        return {"message_id": 300}

    def send_text(self, chat_id, text, keyboard=None):
        self.sent.append((text, keyboard))

    def edit_text(self, chat_id, message_id, text, keyboard=None):
        self.edited.append((text, keyboard))


class GateTests(TestCase):
    def setUp(self):
        self.repo = CatalogRepository()
        self.telegram = FakeTelegram()
        self.user = BotUser.objects.create(telegram_id=10001)
        self.film = Film.objects.create(title="Example", slug="example")
        self.channel = Channel.objects.create(name="My channel", chat_id=-10012345678,
                                              username="mychannel", join_url="https://t.me/mychannel",
                                              require_post_clicks=True)
        self.film.required_channels.add(self.channel)
        self.posts = [ChannelPost.objects.create(channel=self.channel, message_id=i) for i in range(1, 6)]
        self.profile = InstagramTask.objects.create(name="test", url="https://www.instagram.com/example/")

    def test_post_tracking_is_removed_even_with_old_flag_and_new_posts(self):
        gate = GateUsecase(self.repo, self.telegram)
        pending = gate.evaluate(self.user, self.film)
        self.assertEqual(pending.notice_key, "follow_pages")
        self.assertEqual(len(pending.buttons), 1)
        self.assertIn("فالو کردن test", pending.buttons[0][0]["text"])
        self.assertNotIn("پست", str(pending.result.missing))
        self.repo.visit(self.user, self.film, instagram_task=self.profile)
        self.assertTrue(gate.evaluate(self.user, self.film).result.complete)
        ChannelPost.objects.create(channel=self.channel, message_id=6)
        self.assertTrue(gate.evaluate(self.user, self.film).result.complete)

    def test_creator_and_administrator_membership_are_accepted(self):
        self.repo.visit(self.user, self.film, instagram_task=self.profile)
        for status in ("creator", "administrator", "member"):
            with self.subTest(status=status):
                self.telegram.status = status
                snapshot = GateUsecase(self.repo, self.telegram).evaluate(self.user, self.film)
                self.assertTrue(snapshot.result.complete)
                self.assertEqual(snapshot.buttons, [])

    def test_only_missing_prerequisites_are_displayed_after_check(self):
        gate = GateUsecase(self.repo, self.telegram)
        self.telegram.status = "left"
        snapshot = gate.evaluate(self.user, self.film)
        self.assertEqual(snapshot.notice_key, "join_and_follow")
        self.assertEqual(len(snapshot.buttons), 2)
        self.repo.visit(self.user, self.film, instagram_task=self.profile)
        snapshot = gate.evaluate(self.user, self.film)
        self.assertEqual(snapshot.notice_key, "join_channels")
        self.assertEqual(len(snapshot.buttons), 1)
        self.assertIn("عضویت", snapshot.buttons[0][0]["text"])
        self.telegram.status = "administrator"
        self.assertTrue(gate.evaluate(self.user, self.film).result.complete)

    def test_failed_lookup_does_not_claim_user_is_not_joined(self):
        self.telegram.fail_membership = True
        snapshot = GateUsecase(self.repo, self.telegram).evaluate(self.user, self.film)
        self.assertEqual(snapshot.notice_key, "membership_check_unavailable")
        self.assertFalse(snapshot.result.complete)
        self.assertFalse(any("عضویت در" in button[0]["text"] for button in snapshot.buttons))

    def test_check_edits_message_with_short_status_and_remaining_buttons(self):
        self.telegram.status = "left"
        self.repo.visit(self.user, self.film, instagram_task=self.profile)
        usecase = ConversationUsecase(self.telegram, repo=self.repo)
        usecase.execute(UserEvent(self.user.telegram_id, self.user.telegram_id, 123, "callback", "check", self.film.slug))
        text, buttons = self.telegram.edited[-1]
        self.assertEqual(text, "⚠️ هنوز عضو همه کانال‌ها نشده‌اید.")
        self.assertEqual(sum("url" in b for row in buttons for b in row), 1)

    def test_instagram_click_redirects_without_confirmation_or_follow_verification(self):
        url = make_link(self.user.telegram_id, self.film.pk, "instagram", self.profile.pk)
        path = urlsplit(url).path
        response = self.client.get(path)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.profile.url)
        self.assertEqual(LinkVisit.objects.count(), 1)
        self.client.get(path)
        self.assertEqual(LinkVisit.objects.count(), 1)
        self.assertEqual(self.client.post(path).status_code, 405)
        old_post = make_link(self.user.telegram_id, self.film.pk, "post", self.posts[0].pk)
        self.assertEqual(self.client.get(urlsplit(old_post).path).status_code, 400)

    def test_send_records_expiration_row(self):
        source = MediaSource.objects.create(source_chat_id=-1005678, source_message_id=20, media_type="video")
        FilmAsset.objects.create(film=self.film, source=source)
        with patch("backend.apps.cinema.logic.deliver_usecase.time.sleep"):
            result = DeliverFilmUsecase(self.repo, DeliveryRepository(), self.telegram).execute(
                self.user, self.film, self.user.telegram_id
            )
        self.assertEqual(result, "sent")
        self.assertEqual(DeliveredMessage.objects.count(), 1)
        self.assertFalse(DeliveredMessage.objects.first().deleted_at)


class MultiBotGateTests(TestCase):
    def test_central_and_dedicated_channel_admin_status_passes(self):
        bot = BotAccount.objects.create(key="bot01", username="movie_bot")
        central = Channel.objects.create(name="Central", chat_id=-10011111,
                                         join_url="https://t.me/central", is_central=True)
        dedicated = Channel.objects.create(name="Film", chat_id=-10022222,
                                           join_url="https://t.me/film")
        film = Film.objects.create(title="My film", slug="my_film", bot=bot, channel=dedicated)
        user = BotUser.objects.create(telegram_id=100)
        api = FakeTelegram()
        api.status_by_chat_id = {central.chat_id: "administrator", dedicated.chat_id: "creator"}
        snapshot = GateUsecase(CatalogRepository(), api).evaluate(user, film)
        self.assertTrue(snapshot.result.complete)
        self.assertEqual(snapshot.buttons, [])
