from match import MatchStatus

from display import AllStrings as disp

from .process import Process


class GettingReady2(Process, status=MatchStatus.IS_WAITING_2):

    def __init__(self, match):
        self.match = match

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = True

        super().__init__(match)

    @Process.init_loop
    async def init(self):
        await disp.MATCH_CONFIRM.send(self.match.channel, self.match.teams[0].captain.mention,
                                      self.match.teams[1].captain.mention, match=self.match.proxy)

    @Process.public
    async def clear(self, ctx):
        await self.match.clean()
        await disp.MATCH_CLEARED.send(ctx)

    @Process.public
    async def on_team_ready(self, team, ready):
        team.captain.is_turn = not ready
        if ready:
            other = self.match.teams[team.id-1]
            # If other is_turn, then not ready
            # Else everyone ready
            if not other.captain.is_turn:
                await self.match.next_process()
