from match_process import MatchStatus
from modules.reactions import ReactionHandler

from display.strings import AllStrings as disp
from display.classes import ContextWrapper

import match_process.meta as meta
import match_process.common_picking as common
from asyncio import sleep

class MapPicking(meta.Process, status=MatchStatus.IS_BASING):
    
    def __init__(self, match):
        self.match = match

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = True

        super().__init__(match)

    @meta.init_loop
    async def init(self):
        if not self.match.data.base:
            await self.match.base_selector.display_all(self.match.channel,
                                                       mentions=f"{self.match.teams[0].captain.mention} "
                                                                f"{self.match.teams[1].captain.mention}")
        else:
            await self.match.base_selector.show_base_status(self.match.channel)
            self.on_base_found()

    @meta.public
    def on_base_found(self):
        self.match.on_base_pick_over()

    @meta.public
    async def clear(self, ctx):
        await self.match.clean()
        await disp.MATCH_CLEARED.send(ctx)

    @meta.public
    async def sub(self, ctx, subbed):
        await common.after_pick_sub(ctx, self.match, subbed)

    @meta.public
    async def pick_status(self, ctx):
        print(self.match.status)
        await disp.PK_FACTION_INFO.send(ctx)

    @meta.public
    async def pick(self, ctx, captain, args):
        await common.faction_change(ctx, captain, args, self.match)
