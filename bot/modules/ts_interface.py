from modules.ts3 import REGEX_getTs3Bots
import modules.config as cfg
from modules.asynchttp import request_code as http_request

from asyncio import sleep

from asyncio import sleep
from lib.tasks import loop

from logging import getLogger

log = getLogger("pog_bot")

class AudioBot:
    # Add some chacks so we don't have several lines at the same time

    def __init__(self, match):
        self.__num = cfg.channels["matches"].index(match.id)+1

    def drop_match(self):
        audio_string = f"drop_match_{self.__num}_picks"
        _TaskAudio(self.__num).task_audio.start(audio_string, lobby=True)

    def select_teams(self):
        _TaskAudio(self.__num).task_audio.start("select_teams", lobby=False, wait=10)
    
    def select_factions(self):
        _TaskAudio(self.__num).task_audio.start("select_factions")

    def faction_pick(self, team):
        audio_string = f"team_{team.id+1}_{cfg.factions[team.faction]}"
        _TaskAudio(self.__num).task_audio.start(audio_string)

    def select_map(self):
        _TaskAudio(self.__num).task_audio.start("select_map")
    
    def map_selected(self):
        _TaskAudio(self.__num).task_audio.start("map_selected")

    def match_confirm(self):
        _TaskAudio(self.__num).task_audio.start("type_ready")

    def countdown(self):
        # Because of Asyncio not really being full asynchronous stuff, these timings will
        # be fine anyways
        _TaskAudio(self.__num).task_audio.start("30s")
        _TaskAudio(self.__num).task_audio.start("10s", wait=20)
        _TaskAudio(self.__num).task_audio.start("5s", wait=25)
    
    def round_over(self):
        _TaskAudio(self.__num).task_audio.start("round_over")
    
    def switch_sides(self):
        _TaskAudio(self.__num).task_audio.start("switch_sides")


class _TaskAudio:

    lobby = False

    def __init__(self, num):
        self.num = num

    @loop(count=1)
    async def task_audio(self, string, lobby=False, wait=0):
        if wait != 0:
            await sleep(wait)
        await self.__lobby(lobby)
        url = f'http://localhost:58913/api/bot/template/{self.num}(/xecute(/add/{string}.mp3)(/play))'
        code = await http_request(url)
        log.debug(f"CODE: {code} for url {url}")

    async def __lobby(self, bl):
        if _TaskAudio.lobby == bl:
            return
        if bl:
            _TaskAudio.lobby = True
            url = f'http://localhost:58913/api/bot/template/{self.num}(/subscribe/channel/281)'
        else:
            _TaskAudio.lobby = False
            url = f'http://localhost:58913/api/bot/template/{self.num}(/unsubscribe/channel/281)'
        code = await http_request(url)
        log.debug(f"CODE: {code} for url {url}")
