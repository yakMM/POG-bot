import queue

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
        self.available = True
        self.operation_queue = queue.Queue()
        self.initialized = False

    def on_match_launching(self):
        global _ongoing_match
        if _ongoing_match:
            self.available = False
        else:
            self.available = True
            _ongoing_match = self.match
            self.operation_queue.put(("clear", None))
            self.operation_queue.put(("title", f'"Match {self.match.id}"'))
            self.operation_queue.put(("length", f'"{self.match.round_length * 60}"'))

    def on_base_selected(self, base):
        if self.available:
            self.operation_queue.put(("base", f'"{base.id}"'))
            if self.initialized:
                try:
                    self.do_all.start()
                except RuntimeError:
                    pass

    def on_teams_updated(self):
        if self.available:
            for tm in self.match.teams:
                self.operation_queue.put((f"teams/{tm.id+1}", str(tm.players_to_dict).replace("'", '"')))
            try:
                self.do_all.start()
            except RuntimeError:
                pass
            if not self.initialized:
                self.initialized = True

    def on_match_started(self):
        if self.available:
            self.operation_queue.put(("start", None))
            self.do_all.start()

    @loop(count=1)
    async def do_all(self):
        while not self.operation_queue.empty():
            current = self.operation_queue.get()
            await post_request(f"{cfg.general['squittal_url']}/api/{current[0]}", current[1])
            await sleep(1)

    def on_clean(self):
        self.initialized = False
        if self.available:
            global _ongoing_match
            _ongoing_match = None
