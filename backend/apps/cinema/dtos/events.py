from dataclasses import dataclass

@dataclass(frozen=True)
class UserEvent:
    telegram_id: int
    chat_id: int
    message_id: int | None
    callback_id: str | None
    action: str
    argument: str = ""
