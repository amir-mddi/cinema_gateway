"""Telegram command metadata centralized, never in controllers."""

_COMMANDS = {
    "fa": [("start", "شروع و فهرست فیلم‌ها"), ("menu", "فهرست فیلم‌ها"), ("language", "تغییر زبان")],
    "en": [("start", "Start and film catalog"), ("menu", "Film menu"), ("language", "Change language")],
}


def set_commands(api):
    api.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in _COMMANDS["fa"]])
    for language, commands in _COMMANDS.items():
        api.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in commands],
                 language_code=language)
