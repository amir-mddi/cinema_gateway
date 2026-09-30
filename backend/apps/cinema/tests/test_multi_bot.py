"""Multi-bot routing, isolation, per-film channels, and per-bot message expiry."""
from unittest.mock import patch
from django.conf import settings
from django.test import TestCase
from backend.apps.cinema.models import (
    BotAccount, BotUser, Channel, Film, Delivery, MediaSource, DeliveredMessage,
)
from backend.apps.cinema.repositories.catalog_repository import CatalogRepository
from backend.apps.cinema.repositories.delivery_repository import DeliveryRepository
from backend.apps.cinema.logic.assignment_usecase import AssignFilmBotUsecase
from backend.apps.cinema.adapters.bot_credentials import token_for


class MultiBotTests(TestCase):
    def setUp(self):
        self.repo = CatalogRepository()
        self.a = BotAccount.objects.create(key="bot01", username="movie_alpha_bot")
        self.b = BotAccount.objects.create(key="bot02", username="movie_beta_bot")
        self.central = Channel.objects.create(name="Central", chat_id=-10010001,
                                              join_url="https://t.me/central", is_central=True,
                                              require_post_clicks=False)
        self.c1 = Channel.objects.create(name="X", chat_id=-10020001,
                                         join_url="https://t.me/film_x", require_post_clicks=False)
        self.c2 = Channel.objects.create(name="Y", chat_id=-10020002,
                                         join_url="https://t.me/film_y", require_post_clicks=False)
        self.x = Film.objects.create(title="X", slug="x", bot=self.a, channel=self.c1)
        self.y = Film.objects.create(title="Y", slug="y", bot=self.b, channel=self.c2)

    def test_explicit_assignment_and_links_are_stable(self):
        self.assertEqual(self.x.deep_link(), "https://t.me/movie_alpha_bot?start=f_x")
        self.assertEqual(self.y.deep_link(), "https://t.me/movie_beta_bot?start=f_y")
        self.assertEqual(self.repo.film("x", bot=self.b), None)
        self.assertEqual([f.slug for f in self.repo.films(bot=self.a)], ["x"])
        self.assertEqual([f.slug for f in self.repo.films(bot=self.b)], ["y"])

    def test_central_plus_film_channel_are_required_not_other_film_channels(self):
        self.assertEqual({c.pk for c in self.repo.required_channels(self.x)}, {self.central.pk, self.c1.pk})
        self.assertEqual({c.pk for c in self.repo.required_channels(self.y)}, {self.central.pk, self.c2.pk})
        self.x.required_channels.add(self.c2)
        self.assertEqual({c.pk for c in self.repo.required_channels(self.x)}, {self.central.pk, self.c1.pk, self.c2.pk})

    def test_processed_ids_namespaced_per_bot(self):
        deliveries = DeliveryRepository()
        self.assertTrue(deliveries.begin_update(self.a, 111))
        self.assertTrue(deliveries.begin_update(self.b, 111))
        self.assertFalse(deliveries.begin_update(self.a, 111))
        self.assertTrue(deliveries.update_processed(self.b, 111))

    def test_expiration_message_records_sending_bot(self):
        user = BotUser.objects.create(telegram_id=123)
        repo = DeliveryRepository()
        d1 = repo.create(user, self.x)
        d2 = repo.create(user, self.y)
        m1 = repo.record_message(d1, chat_id=user.telegram_id, message_id=42, ttl_seconds=30)
        m2 = repo.record_message(d2, chat_id=user.telegram_id, message_id=42, ttl_seconds=30)
        self.assertNotEqual(m1.pk, m2.pk)
        self.assertEqual(m1.bot_id, self.a.id)
        self.assertEqual(m2.bot_id, self.b.id)

    @patch.dict("os.environ", {"BOT_TOKEN_BOT01": "token-alpha", "BOT_TOKEN_BOT02": "token-beta"})
    def test_manual_or_random_bot_choice(self):
        self.assertEqual(token_for(self.a), "token-alpha")
        with patch("backend.apps.cinema.logic.assignment_usecase.secrets.choice", return_value=self.b):
            self.assertEqual(AssignFilmBotUsecase(self.repo).choose(), self.b)
        self.assertEqual(self.x.bot, self.a)  # picking for another film never changes old links

    def test_channel_reuse_for_two_films_is_prevented(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Film.objects.create(title="Duplicate", slug="duplicate", bot=self.a, channel=self.c1)

    def test_direct_message_source_is_bot_owned_and_storage_is_shared(self):
        with patch.dict("os.environ", {"BOT_TOKEN_BOT01": "token-alpha"}):
            source = self.repo.record_media(123, 50, "video", "movie x", bot=self.a)[0]
        source2 = self.repo.record_media(123, 50, "video", "movie y", bot=self.b)[0]
        self.assertNotEqual(source.pk, source2.pk)
        self.assertEqual(source.bot_id, self.a.id)
        self.assertEqual(source2.bot_id, self.b.id)
