from logging import getLogger

from .plugin import Plugin

log = getLogger("pog_bot")


class SimpleLogger(Plugin):

    def __init__(self, match):
        super().__init__(match)

    def event(self, name):
        log.info(f"Match {self.match.id}: event received: {name}")

    def on_match_launching(self):
        self.event("on_match_launching")

    def on_captain_selected(self):
        self.event("on_captain_selected")

    def on_teams_done(self):
        self.event("on_teams_done")

    def on_faction_pick(self, team):
        self.event("on_faction_pick")

    def on_factions_picked(self):
        self.event("on_factions_picked")

    def on_base_selected(self, base):
        self.event("on_base_selected")

    def on_team_ready(self, team):
        self.event("on_team_ready")

    def on_match_starting(self):
        self.event("on_match_starting")

    def on_round_over(self):
        self.event("on_round_over")

    def on_match_over(self):
        self.event("on_match_over")
