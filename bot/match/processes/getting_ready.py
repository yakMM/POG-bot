from match import MatchStatus

from display import AllStrings as disp

from .process import Process
from match.common import after_pick_sub

import modules.accounts_handler as accounts
import modules.census as census


class GettingReady(Process, status=MatchStatus.IS_WAITING):

    def __init__(self, match):
        self.match = match

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = True

        super().__init__(match)

    @Process.init_loop
    async def init(self):
        await disp.ACC_SENDING.send(self.match.channel)

        for tm in self.match.teams:
            for a_player in tm.players:
                if not a_player.has_own_account:
                    success = await accounts.give_account(a_player)
                    if success:
                        self.match.players_with_account.append(a_player)
                    else:
                        await disp.ACC_NOT_ENOUGH.send(self.match.channel)
                        await self.clear()
                        return

        # Try to send the accounts:
        for a_player in self.match.players_with_account:
            await accounts.send_account(self.match.channel, a_player)

        await disp.ACC_SENT.send(self.match.channel)

        await disp.MATCH_CONFIRM.send(self.match.channel, self.match.teams[0].captain.mention,
                                      self.match.teams[1].captain.mention, match=self.match.proxy)

    @Process.public
    async def clear(self, ctx):
        await self.match.clean()
        await disp.MATCH_CLEARED.send(ctx)

    @Process.public
    async def on_team_ready(self, team, ready):
        team.captain.is_turn = not ready
        team.on_team_ready(ready)
        if ready:
            other = self.match.teams[team.id-1]
            # If other is_turn, then not ready
            # Else everyone ready
            if not other.captain.is_turn:
                await self.match.next_process()

    @Process.public
    async def remove_account(self, a_player):
        await accounts.terminate_account(a_player)
        self.match.players_with_account.remove(a_player)

    @Process.public
    async def give_account(self, a_player):
        success = await accounts.give_account(a_player)
        if success:
            self.match.players_with_account.append(a_player)
            await accounts.send_account(self.match.channel, a_player)
            await disp.ACC_GIVING.send(self.match.channel, a_player.mention)
        else:
            await disp.ACC_NOT_ENOUGH.send(self.match.channel)
            await self.clear()

    @Process.public
    async def do_sub(self, subbed, force_player):
        new_player = await after_pick_sub(self.match, subbed, force_player, clean_subbed=False)
        if not new_player:
            return
        if not subbed.active.has_own_account:
            await self.remove_account(subbed.active)
            subbed.on_player_clean()
        if not new_player.active.has_own_account:
            await self.give_account(new_player.active)

    @Process.public
    async def pick_status(self, ctx):
        await disp.PK_FACTION_INFO.send(ctx)
