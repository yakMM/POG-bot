from display import AllStrings as disp
from asyncio import sleep
from datetime import datetime as dt, timezone as tz
from lib.tasks import Loop, loop

from match import MatchStatus
from .process import Process

import modules.config as cfg
import modules.reactions as reactions


class MatchPlaying(Process, status=MatchStatus.IS_STARTING):

    def __init__(self, match):
        self.match = match
        self.match_loop = Loop(coro=self.on_match_over, minutes=cfg.general["round_length"], delay=1, count=2)

        self.rh = reactions.SingleMessageReactionHandler(remove_msg=True)

        @self.rh.reaction('🔁')
        async def refresh_info(reaction, player, user, msg):
            await disp.PK_SHOW_TEAMS.edit(self.rh.msg, match=self.match.proxy)

        super().__init__(match)

    @Process.init_loop
    async def init(self):
        await self.match.base_selector.clean()
        self.match.base_selector = None
        await disp.MATCH_STARTING_1.send(self.match.channel, self.match.round_no, "30")
        await sleep(10)
        await disp.MATCH_STARTING_2.send(self.match.channel, self.match.round_no, "20")
        await sleep(10)
        await disp.MATCH_STARTING_2.send(self.match.channel, self.match.round_no, "10")
        await sleep(10)
        player_pings = [" ".join(tm.all_pings) for tm in self.match.teams]
        await disp.MATCH_STARTED.send(self.match.channel, *player_pings, self.match.round_no)
        self.match.round_stamps.append(int(dt.timestamp(dt.now())))
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
        await disp.MATCH_ROUND_OVER.send(self.match.channel, *player_pings, self.match.round_no)
        await self.rh.destroy()
        # for tm in self.__teams:
        #     tm.captain.is_turn = True
        # if self.round_no < 2:
        #     self.__audio_bot.switch_sides()
        #     await send("MATCH_SWAP", self.__channel)
        #     self.__status = MatchStatus.IS_WAITING
        #     captain_pings = [tm.captain.mention for tm in self.__teams]
        #     self.__audio_bot.match_confirm()
        #     await send("MATCH_CONFIRM", self.__channel, *captain_pings, match=self)
        #     self._score_calculation.start()
        #     return
        # await send("MATCH_OVER", self.__channel)
        # self.__status = MatchStatus.IS_RESULT
        # try:
        #     await process_score(self)
        #     self.__result_msg = await publish_match_image(self)
        # except Exception as e:
        #     log.error(f"Error in score or publish function!\n{e}")
        # try:
        #     await update_match(self)
        # except Exception as e:
        #     log.error(f"Error in match database push!\n{e}")
        # await self.clear()

    @Process.public
    async def clear(self, ctx):
        self.auto_info_loop.cancel()
        self.match_loop.cancel()
        await self.rh.destroy()
        await self.match.clean()
        await disp.MATCH_CLEARED.send(ctx)


