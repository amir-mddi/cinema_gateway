from django.conf import settings
from django.core import signing

SALT = "cinema.visits.v1"


def make_link(telegram_id: int, film_id: int, kind: str, target_id: int) -> str:
    token = signing.dumps([telegram_id, film_id, kind, target_id], salt=SALT, compress=True)
    return f"{settings.PUBLIC_BASE_URL}/out/{token}/"


def parse_link(token: str):
    value = signing.loads(token, salt=SALT, max_age=60 * 60 * 6)
    if not isinstance(value, list) or len(value) != 4:
        raise signing.BadSignature("Invalid link")
    if not all(isinstance(x, int) and x > 0 for x in (value[0], value[1], value[3])):
        raise signing.BadSignature("Invalid identifiers")
    if value[2] != "instagram":
        raise signing.BadSignature("Invalid click kind")
    return value
