from match import MatchStatus
from .process import Process

from display.strings import AllStrings as disp


class BasePicking(Process, status=MatchStatus.IS_BASING):
    
    def __init__(self, match):
        self.match = match
        super().__init__(match)

    @Process.init_loop
    async def init(self):
        if not self.match.base:
            await self.match.base_selector.display_all(self.match.channel,
                                                       mentions=f"{self.match.teams[0].captain.mention} "
                                                                f"{self.match.teams[1].captain.mention}")
        else:
            await self.match.base_selector.show_base_status(self.match.channel)
            self.on_base_found()

    @Process.public
    def on_base_found(self):
        self.match.next_process()
        self.match.plugin_manager.on_base_selected(self.match.base)

    @Process.public
    async def clear(self, ctx):
        await self.match.clean()
        await disp.MATCH_CLEARED.send(ctx)

    @Process.public
    async def pick_status(self, ctx):
        await disp.PK_BASING_INFO.send(ctx)
