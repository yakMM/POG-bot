from match import MatchStatus

from display import AllStrings as disp, ContextWrapper
from logging import getLogger

from .process import Process
from match.common import after_pick_sub

import modules.accounts_handler as accounts
import modules.census as census
import modules.reactions as reactions

from match.common import get_check_captain
from modules.asynchttp import ApiNotReachable

log = getLogger("pog_bot")


class GettingReady(Process, status=MatchStatus.IS_WAITING):

    def __init__(self, match):
        self.match = match

        if self.match.round_no > 0:
            super().change_status(MatchStatus.IS_WAITING_2)
            self.is_first_round = False
        else:
            self.is_first_round = True

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = True

        self.rh = reactions.SingleMessageReactionHandler()

        @self.rh.reaction('✅')
        async def on_ready_reaction(reaction, player, user, msg):
            if not player.active:
                raise reactions.UserLackingPermission
            if player.active not in (self.match.teams[0].captain, self.match.teams[1].captain):
                raise reactions.UserLackingPermission
            ctx = ContextWrapper.wrap(self.match.channel)
            ctx.author = user
            ctx.cmd_name = "ready"
            await self.ready(ctx, player.active)

        super().__init__(match)

    @Process.init_loop
    async def init(self):
        if self.is_first_round:
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

        msg = await disp.MATCH_CONFIRM.send(self.match.channel, self.match.teams[0].captain.mention,
                                            self.match.teams[1].captain.mention, match=self.match.proxy)
        await self.rh.set_new_msg(msg)

    @Process.public
    async def clear(self, ctx):
        self.rh.clear()
        await self.match.clean_all_auto()
        await disp.MATCH_CLEARED.send(ctx)

    @Process.public
    async def info(self):
        msg = await disp.PK_SHOW_TEAMS.send(self.match.channel, match=self.match.proxy)
        await self.rh.set_new_msg(msg)

    def on_team_ready(self, team, ready):
        team.captain.is_turn = not ready
        if ready:
            self.match.plugin_manager.on_team_ready(team)
        if self.is_first_round:
            team.on_team_ready(ready)
            if ready:
                self.match.base_selector.clean()
                self.match.command_factory.on_team_ready(team)

    def ready_check(self, team):
        other = self.match.teams[team.id - 1]
        # If other is_turn, then not ready
        # Else everyone ready
        if not other.captain.is_turn:
            self.rh.clear()
            self.match.ready_next_process()
            if self.is_first_round:
                for tm in self.match.teams:
                    tm.on_match_starting()
                    self.match.data.teams[tm.id] = tm.team_score
            return True
        return False

    @Process.public
    async def ready(self, ctx, captain):
        if not captain.is_turn:
            self.on_team_ready(captain.team, False)
            msg = await disp.MATCH_TEAM_UNREADY.send(ctx, captain.team.name, match=self.match.proxy)
            await self.rh.set_new_msg(msg)
            return
        if captain.is_turn:
            if self.match.check_validated:
                not_validated_players = accounts.get_not_validated_accounts(captain.team)
                if len(not_validated_players) != 0:
                    await disp.MATCH_PLAYERS_NOT_READY.send(ctx, captain.team.name,
                                                            " ".join(p.mention for p in not_validated_players))
                    return
            if self.match.check_offline:
                try:
                    offline_players = await census.get_offline_players(captain.team)
                    if len(offline_players) != 0:
                        await disp.MATCH_PLAYERS_OFFLINE.send(ctx, captain.team.name,
                                                              " ".join(p.mention for p in offline_players),
                                                              p_list=offline_players)
                        return
                except ApiNotReachable as e:
                    log.error(f"ApiNotReachable caught when checking online players: {e.url}")
                    await disp.API_READY_ERROR.send(ctx)
            self.on_team_ready(captain.team, True)
            is_over = self.ready_check(captain.team)
            msg = await disp.MATCH_TEAM_READY.send(ctx, captain.team.name, match=self.match.proxy)
            if is_over:
                self.match.start_next_process()
            else:
                await self.rh.set_new_msg(msg)

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
