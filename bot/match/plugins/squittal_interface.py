import modules.config as cfg
from modules.asynchttp import request_code as http_request, post_request
from lib.tasks import loop, Loop

from asyncio import sleep
from logging import getLogger

from .plugin import Plugin

log = getLogger("pog_bot")

_ongoing_match = None


class SquittalInterface(Plugin):

    def __init__(self, match):
        super().__init__(match)
        self.num = cfg.channels["matches"].index(match.channel.id) + 1
        self.lobby = False
        self.available = True

    def on_match_launching(self):
        global _ongoing_match
        if _ongoing_match:
            self.available = False
            return
        _ongoing_match = self.match
        self.match_start.start()

    def on_base_selected(self, base):
        if self.available:
            Loop(coro=post_request, count=1).start(f"{cfg.general['squittal_url']}/api/base",
                                                   f'"{self.match.base.id}"')

    def on_teams_updated(self):
        if self.available:
            for tm in self.match.teams:
                print(str(tm.players_to_dict).replace("'", '"'))
                Loop(coro=post_request, count=1).start(f"{cfg.general['squittal_url']}/api/teams/{tm.id+1}",
                                                       str(tm.players_to_dict).replace("'", '"'))

    def on_match_started(self):
        if self.available:
            Loop(coro=post_request, count=1).start(f"{cfg.general['squittal_url']}/api/start")

    @loop(count=1)
    async def match_start(self):
        await sleep(1)
        await post_request(f"{cfg.general['squittal_url']}/api/clear")
        await sleep(1)
        await post_request(f"{cfg.general['squittal_url']}/api/title", f'"Match {self.match.id}"')
        await sleep(1)
        await post_request(f"{cfg.general['squittal_url']}/api/length", f'"{self.match.round_length * 60}"')

    def on_clean(self):
        if self.available:
            global _ongoing_match
            _ongoing_match = None
