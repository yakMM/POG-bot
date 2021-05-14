import modules.config as cfg
from modules.asynchttp import request_code as http_request, post_request
from lib.tasks import loop, Loop

from asyncio import sleep
from logging import getLogger

from .plugin import Plugin

log = getLogger("pog_bot")


class SquittalInterface(Plugin):

    def __init__(self, match):
        super().__init__(match)
        self.num = cfg.channels["matches"].index(match.channel.id) + 1
        self.lobby = False

    def on_match_launching(self):
        Loop(coro=post_request, count=1).start(f"https://localhost:5001/api/title",
                                               f"Match {self.match.id}")
        Loop(coro=post_request, count=1).start(f"https://localhost:5001/api/length",
                                               str(self.match.round_length * 60))

    def on_base_selected(self, base):
        Loop(coro=post_request, count=1).start(f"https://localhost:5001/api/base",
                                               str(self.match.base.id))

    def on_match_starting(self):
        for tm in self.match.teams:
            Loop(coro=post_request, count=1).start(f"https://localhost:5001/api/teams/{tm.id+1}",
                                                   tm.team_score.ig_ids_list)

    def on_match_started(self):
        Loop(coro=post_request, count=1).start(f"https://localhost:5001/api/start", "")



