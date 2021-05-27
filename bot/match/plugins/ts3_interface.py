import modules.config as cfg
from modules.asynchttp import request_code as http_request
from lib.tasks import loop, Loop

from asyncio import sleep
from logging import getLogger

from .plugin import Plugin

log = getLogger("pog_bot")


class AudioBot(Plugin):
    # (note: thanks to the queue system of the TS3AudioBot, two audio won't
    # conflict)
    # Maybe add some checks between different matches anyways

    def __init__(self, match):
        super().__init__(match)
        self.num = cfg.channels["matches"].index(match.channel.id) + 1
        self.lobby = False

    def on_match_launching(self):
        Loop(coro=configure, count=1).start(self.num)
        audio_string = f"drop_match_{self.num}_picks"
        _TaskAudio(self).task_audio.start(audio_string, lobby=True, wait=0)

    def on_captains_selected(self):
        _TaskAudio(self).task_audio.start("select_teams", lobby=False)

    def on_teams_done(self):
        _TaskAudio(self).task_audio.start("select_factions")

    def on_faction_pick(self, team):
        audio_string = f"team_{team.id + 1}_{cfg.factions[team.faction]}"
        _TaskAudio(self).task_audio.start(audio_string)

    def on_factions_picked(self):
        if not self.match.base:
            _TaskAudio(self).task_audio.start("select_base")

    def on_base_selected(self, base):
        _TaskAudio(self).task_audio.start("base_selected", wait=0)
        _TaskAudio(self).task_audio.start(f'base_{cfg.id_to_base[base.id]}', wait=1)
        _TaskAudio(self).task_audio.start("type_ready", wait=2)

    def on_team_ready(self, team):
        audio_string = f"team_{team.id + 1}_ready"
        _TaskAudio(self).task_audio.start(audio_string)

    def on_match_starting(self):
        # Timing tested
        _TaskAudio(self).task_audio.start("30s", wait=0)
        _TaskAudio(self).task_audio.start("10s", wait=20)
        _TaskAudio(self).task_audio.start("5s", wait=25)

    def on_round_over(self):
        _TaskAudio(self).task_audio.start("round_over")
        if self.match.round_no == 1:
            _TaskAudio(self).task_audio.start("switch_sides", wait=0)
            _TaskAudio(self).task_audio.start("type_ready", wait=1)

    def on_clean(self):
        self.lobby = False


class _TaskAudio:

    def __init__(self, bot):
        self.bot = bot

    @loop(count=1)
    async def task_audio(self, string, lobby=False, wait=-1):
        if wait >= 0:
            await sleep(wait)
        await self.__lobby(lobby)
        url = f'{cfg.ts["url"]}/api/bot/template/{self.bot.num}(/xecute(/add/{string}.mp3)(/play))'
        await _send_url(url)

    async def __lobby(self, bl):
        if self.bot.lobby == bl:
            return
        if bl:
            self.bot.lobby = True
            url = f'{cfg.ts["url"]}/api/bot/template/{self.bot.num}(/subscribe/channel/{cfg.ts["lobby_id"]})'
        else:
            self.bot.lobby = False
            url = f'{cfg.ts["url"]}/api/bot/template/{self.bot.num}(/unsubscribe/channel/{cfg.ts["lobby_id"]})'
        await _send_url(url)


async def _send_url(url):
    try:
        code = await http_request(url)
        if code != 204:
            log.warning(f'TS3Bot API: Received code {code} on {url}')
    except Exception as e:
        log.warning(f"Couldn't join TS3 bot on {url}\n{e}")


async def configure(num):
    channels_str = "/".join(str(c_id) for c_id in cfg.ts["matches"][num - 1])
    url = f'{cfg.ts["url"]}/api/bot/template/{num}(/subscribe/channel/{channels_str})'
    try:
        await _send_url(url)
    except Exception as e:
        log.warning(f"Couldn't configure TS3 bot on {url}\n{e}")

