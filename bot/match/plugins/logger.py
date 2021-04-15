from logging import getLogger

from .plugin import Plugin
from modules.tools import timestamp_now
import modules.database as db
import modules.config as cfg

log = getLogger("pog_bot")


class SimpleLogger(Plugin):

    def __init__(self, match):
        super().__init__(match)
        self.data = dict()

    def __event(self, name):
        log.info(f"Match {self.match.id}: event received: {name}")

    def __auto_dict_add(self, key, doc):
        if key in self.data:
            self.data[key].append(doc)
        else:
            self.data[key] = [doc]

    def on_match_launching(self):
        self.data = {"_id": self.match.id, "match_launching": timestamp_now()}
        self.__event("on_match_launching")

    def on_captain_selected(self, i, player):
        self.__auto_dict_add("captains", {"team": i, "timestamp": timestamp_now(), "player": player.id})
        self.__event(f"on_captain_selected: id: [{player.id}], name: [{player.name}]")

    def on_captains_selected(self):
        self.__event("on_captains_selected")

    def on_teams_done(self):
        self.data["teams_done"] = timestamp_now()
        self.__event("on_teams_done")

    def on_faction_pick(self, team):
        self.__auto_dict_add("factions",
                             {"team": team.id, "timestamp": timestamp_now(), "faction": cfg.factions[team.faction]})
        self.__event(f"on_faction_pick: team: [{team.id}] picked: [{cfg.factions[team.faction]}]")

    def on_factions_picked(self):
        self.__event("on_factions_picked")

    def on_base_selected(self, base):
        self.data["base"]: base.id
        self.__event("on_base_selected")

    def on_team_ready(self, team):
        self.__event(f"on_team_ready: team: [{team.id}]")

    def on_match_starting(self):
        self.__auto_dict_add("rounds",
                             {"round_number": self.match.round_no, "event": "starting", "timestamp": timestamp_now()})
        self.__event("on_match_starting")

    def on_round_over(self):
        self.__auto_dict_add("rounds",
                             {"round_number": self.match.round_no, "event": "stopping", "timestamp": timestamp_now()})
        self.__event("on_round_over")

    def on_match_over(self):
        self.data["match_over"] = timestamp_now()
        self.__event("on_match_over")

    async def clean(self):
        await db.async_db_call(db.set_element, "match_logs", self.match.id, self.data)
        self.data.clear()
