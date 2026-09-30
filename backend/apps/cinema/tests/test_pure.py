import unittest
from backend.apps.cinema.vo.callbacks import parse_start, start_parameter, callback
from backend.apps.cinema.entities.policies import membership_ok
from backend.apps.cinema.vo.texts import t


class SimpleRulesTests(unittest.TestCase):
    def test_start_and_callback(self):
        self.assertEqual(parse_start(start_parameter("my-film_01")), "my-film_01")
        self.assertIsNone(parse_start("f_../../nope"))
        with self.assertRaises(ValueError):
            start_parameter("x" * 49)
        with self.assertRaises(ValueError):
            callback("x" * 70)

    def test_membership(self):
        self.assertTrue(membership_ok({"status": "member"}))
        self.assertTrue(membership_ok({"status": "administrator"}))
        self.assertTrue(membership_ok({"status": "creator"}))
        self.assertTrue(membership_ok({"status": "restricted", "is_member": True}))
        self.assertFalse(membership_ok({"status": "restricted", "is_member": False}))
        self.assertFalse(membership_ok({"status": "left"}))
        self.assertFalse(membership_ok({"status": "kicked"}))

    def test_texts(self):
        self.assertIn("فیلم", t("fa", "welcome"))
        self.assertIn("film", t("en", "welcome").lower())
