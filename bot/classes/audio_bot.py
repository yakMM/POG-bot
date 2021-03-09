import modules.config as cfg
from modules.asynchttp import request_code as http_request
from lib.tasks import loop

from asyncio import sleep
from logging import getLogger

log = getLogger("pog_bot")


class AudioBot:
    # TODO: Add some checks so we don't have several lines at the same time
    # in the lobby for example
    # (note: thanks to the queue system of the TS3AudioBot, two audio won't
    # conflict)

    def __init__(self, match):
        self.num = cfg.channels["matches"].index(match.channel.id) + 1
        self.lobby = False

    def drop_match(self):
        audio_string = f"drop_match_{self.num}_picks"
        _TaskAudio(self).task_audio.start(audio_string, lobby=True)

    def select_teams(self):
        _TaskAudio(self).task_audio.start("select_teams", lobby=False, wait=10)

    def select_factions(self):
        _TaskAudio(self).task_audio.start("select_factions")

    def faction_pick(self, team):
        audio_string = f"team_{team.id + 1}_{cfg.factions[team.faction]}"
        _TaskAudio(self).task_audio.start(audio_string)

    def select_base(self):
        _TaskAudio(self).task_audio.start("select_base")

    def base_selected(self, base):
        _TaskAudio(self).task_audio.start("base_selected")
        _TaskAudio(self).task_audio.start(f'base_{cfg.id_to_base[base.id]}', wait=1)

    def match_confirm(self):
        _TaskAudio(self).task_audio.start("type_ready")

    def team_ready(self, team):
        audio_string = f"team_{team.id + 1}_ready"
        _TaskAudio(self).task_audio.start(audio_string)

    def countdown(self):
        # Timing tested
        _TaskAudio(self).task_audio.start("30s")
        _TaskAudio(self).task_audio.start("10s", wait=20)
        _TaskAudio(self).task_audio.start("5s", wait=25)

    def round_over(self):
        _TaskAudio(self).task_audio.start("round_over")

    def switch_sides(self):
        _TaskAudio(self).task_audio.start("switch_sides")


class _TaskAudio:

    def __init__(self, bot):
        self.bot = bot

    @loop(count=1)
    async def task_audio(self, string, lobby=False, wait=0):
        if wait != 0:
            await sleep(wait)
        await self.__lobby(lobby)
        url = f'http://localhost:58913/api/bot/template/{self.bot.num}(/xecute(/add/{string}.mp3)(/play))'
        await _send_url(url)

    async def __lobby(self, bl):
        if self.bot.lobby == bl:
            return
        if bl:
            self.bot.lobby = True
            url = f'http://localhost:58913/api/bot/template/{self.bot.num}(/subscribe/channel/281)'
        else:
            self.bot.lobby = False
            url = f'http://localhost:58913/api/bot/template/{self.bot.num}(/unsubscribe/channel/281)'
        await _send_url(url)


async def _send_url(url):
    code = await http_request(url)
    if code != 204:
        log.warning(f'TS3Bot API: Received code {code} on {url}')
