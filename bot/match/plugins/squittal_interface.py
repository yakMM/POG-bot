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
        self.match_start.start()

    def on_base_selected(self, base):
        Loop(coro=post_request, count=1).start(f"{cfg.general['squittal_url']}/api/base",
                                               str(self.match.base.id))

    def on_match_starting(self):
        for tm in self.match.teams:
            Loop(coro=post_request, count=1).start(f"{cfg.general['squittal_url']}/api/teams/{tm.id+1}",
                                                   tm.team_score.ig_ids_list)

    def on_match_started(self):
        Loop(coro=post_request, count=1).start(f"{cfg.general['squittal_url']}/api/start")


    @loop(count=1)
    async def match_start(self):
        await post_request(f"{cfg.general['squittal_url']}/api/clear")
        await sleep(1)
        await post_request(f"{cfg.general['squittal_url']}/api/title", f"Match {self.match.id}")
        await sleep(1)
        await post_request(f"{cfg.general['squittal_url']}/api/length", str(self.match.round_length * 60))






