from backend.apps.cinema.enums.bot_enums import ButtonStyle
from backend.apps.cinema.vo.callbacks import callback
from backend.apps.cinema.vo.texts import t


class KeyboardFactory:
    def menu(self, user, films, offset=0):
        rows = [[{"text": f"🎬 {film.title}", "callback_data": callback("film", film.slug),
                  "style": ButtonStyle.PRIMARY}] for film in films]
        if offset > 0:
            rows.append([{"text": t(user.language, "prev_page"), "callback_data": callback("menu", str(max(0, offset-8)))}])
        if len(films) == 8:
            rows.append([{"text": t(user.language, "next_page"), "callback_data": callback("menu", str(offset+8))}])
        rows.append([{"text": t(user.language, "language"), "callback_data": "language", "style": ButtonStyle.PRIMARY}])
        return rows

    def language(self):
        return [[{"text": "🇮🇷 فارسی", "callback_data": "lang:fa", "style": ButtonStyle.SUCCESS},
                 {"text": "🇬🇧 English", "callback_data": "lang:en", "style": ButtonStyle.PRIMARY}],
                [{"text": "🏠", "callback_data": "menu:0"}]]

    def requirements(self, user, film, snapshot):
        rows = list(snapshot.buttons)
        rows.append([{"text": t(user.language, "check"), "callback_data": callback("check", film.slug),
                      "style": ButtonStyle.SUCCESS}])
        rows.append([{"text": t(user.language, "menu"), "callback_data": "menu:0"}])
        return rows

    def ready(self, user, film):
        return [[{"text": t(user.language, "watch"), "callback_data": callback("watch", film.slug),
                 "style": ButtonStyle.SUCCESS}],
                [{"text": t(user.language, "menu"), "callback_data": "menu:0"}]]
