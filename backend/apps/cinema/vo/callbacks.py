import re

_FILM = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")


def valid_slug(slug: str) -> bool:
    return bool(_FILM.fullmatch(slug))


def start_parameter(slug: str) -> str:
    if not valid_slug(slug):
        raise ValueError("Invalid film slug")
    return f"f_{slug}"


def parse_start(value: str) -> str | None:
    if not value.startswith("f_"):
        return None
    slug = value[2:]
    return slug if valid_slug(slug) else None


def callback(action: str, slug: str = "") -> str:
    value = f"{action}:{slug}" if slug else action
    if len(value.encode()) > 64:
        raise ValueError("Callback exceeds Telegram limit")
    return value
