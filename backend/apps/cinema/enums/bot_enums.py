from enum import StrEnum

class Language(StrEnum):
    FA = "fa"
    EN = "en"

class ClickKind(StrEnum):
    INSTAGRAM = "instagram"

class Callback(StrEnum):
    CHECK = "check"
    MENU = "menu"
    LANGUAGE = "lang"
    WATCH = "watch"

class ButtonStyle(StrEnum):
    PRIMARY = "primary"
    SUCCESS = "success"
    DANGER = "danger"
