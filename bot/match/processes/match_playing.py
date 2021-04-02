from display import AllStrings as disp
from asyncio import sleep
from datetime import datetime as dt, timezone as tz
from lib.tasks import Loop, loop

from match import MatchStatus
from .process import Process

import modules.config as cfg
import modules.reactions as reactions

from match.classes.base_selector import push_last_bases

import modules.census as census
import modules.tools as tools
import modules.image_maker as i_maker


class MatchPlaying(Process, status=MatchStatus.IS_STARTING):

    def __init__(self, match):
        self.match = match
        self.match_loop = Loop(coro=self.on_match_over, minutes=match.round_length, delay=1, count=2)

        self.rh = reactions.SingleMessageReactionHandler(remove_msg=True)

        @self.rh.reaction('🔁')
        async def refresh_info(reaction, player, user, msg):
            await disp.PK_SHOW_TEAMS.edit(self.rh.msg, match=self.match.proxy)

        super().__init__(match)

    @Process.init_loop
    async def init(self):
        if self.match.base_selector:
            await self.match.base_selector.clean()
            push_last_bases(self.match.base)
            self.match.base_selector = None
        await disp.MATCH_STARTING_1.send(self.match.channel, self.match.round_no, "30")
        await sleep(10)
        await disp.MATCH_STARTING_2.send(self.match.channel, self.match.round_no, "20")
        await sleep(10)
        await disp.MATCH_STARTING_2.send(self.match.channel, self.match.round_no, "10")
        await sleep(10)
        player_pings = [" ".join(tm.all_pings) for tm in self.match.teams]
        await disp.MATCH_STARTED.send(self.match.channel, *player_pings, self.match.round_no)
        self.match.round_stamps.append(tools.timestamp_now())
        super().change_status(MatchStatus.IS_PLAYING)
        self.match_loop.start()
        self.auto_info_loop.start()

    @Process.public
    async def info(self, ctx=None):
        msg = await disp.PK_SHOW_TEAMS.send(self.match.channel, match=self.match.proxy)
        await self.rh.set_new_msg(msg)

    @loop(seconds=15)
    async def auto_info_loop(self):
        if self.rh.is_msg:
            await disp.PK_SHOW_TEAMS.edit(self.rh.msg, match=self.match.proxy)
        else:
            await self.info()

    @Process.public
    def get_formatted_time_to_round_end(self):
        secs = self.get_seconds_to_round_end()
        return f"{secs // 60}m {secs % 60}s"

    def get_seconds_to_round_end(self):
        time_delta = self.match_loop.next_iteration - dt.now(tz.utc)
        return int(time_delta.total_seconds())

    async def on_match_over(self):
        player_pings = [" ".join(tm.all_pings) for tm in self.match.teams]
        self.auto_info_loop.cancel()
        await self.match.set_status(MatchStatus.IS_RUNNING)
        await self.rh.destroy()
        await disp.MATCH_ROUND_OVER.send(self.match.channel, *player_pings, self.match.round_no)
        await census.process_score(self.match.proxy)
        await i_maker.publish_match_image(self.match)
        await self.match.next_process()

    @Process.public
    async def clear(self, ctx):
        self.auto_info_loop.cancel()
        self.match_loop.cancel()
        await self.rh.destroy()
        player_pings = [" ".join(tm.all_pings) for tm in self.match.teams]
        await disp.MATCH_ROUND_OVER.send(self.match.channel, *player_pings, self.match.round_no)
        await disp.MATCH_OVER.send(self.match.channel)
        await self.match.clean()
        await disp.MATCH_CLEARED.send(ctx)


