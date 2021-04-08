from logging import getLogger

from .plugin import Plugin
from modules.tools import timestamp_now
import modules.database as db

log = getLogger("pog_bot")


class SimpleLogger(Plugin):

    def __init__(self, match):
        super().__init__(match)
        self.data = {"_id": match.id}

    def __event(self, name):
        log.info(f"Match {self.match.id}: event received: {name}")

    def on_match_launching(self):
        self.__event("on_match_launching")

    def on_captain_selected(self):
        self.__event("on_captain_selected")

    def on_teams_done(self):
        self.__event("on_teams_done")

    def on_faction_pick(self, team):
        self.__event("on_faction_pick")

    def on_factions_picked(self):
        self.__event("on_factions_picked")

    def on_base_selected(self, base):
        self.__event("on_base_selected")

    def on_team_ready(self, team):
        self.__event("on_team_ready")

    def on_match_starting(self):
        self.__event("on_match_starting")

    def on_round_over(self):
        self.__event("on_round_over")

    def on_match_over(self):
        self.__event("on_match_over")
        self.data["match_over"] = timestamp_now()

    async def clean(self):
        self.data["cleaning"] = timestamp_now()
        await db.async_db_call(db.set_element, "match_logs", self.match.id, self.data)
