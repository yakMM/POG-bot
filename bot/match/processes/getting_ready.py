import asyncio

import discord

from match import MatchStatus

from display import AllStrings as disp, ContextWrapper, views
from logging import getLogger

from .process import Process
from match.common import after_pick_sub

import modules.accounts_handler as accounts
import modules.census as census
import match.classes.interactions as interactions

from modules.asynchttp import ApiNotReachable

log = getLogger("pog_bot")


class GettingReady(Process, status=MatchStatus.IS_WAITING):

    def __init__(self, match):
        self.match = match

        if self.match.round_no > 0:
            self.is_first_round = False
        else:
            self.is_first_round = True

        self.match.teams[1].captain.is_turn = True
        self.match.teams[1].on_team_ready(False)
        self.match.teams[0].captain.is_turn = True
        self.match.teams[0].on_team_ready(False)

        self.getting_ready = [False, False]

        self.ih = interactions.CaptainInteractionHandler(self.match, views.ready_button, check_turn=False,
                                                         disable_after_use=False)

        @self.ih.callback('ready')
        async def on_ready(captain, interaction_id, interaction, interaction_values):
            ctx = ContextWrapper.wrap(self.match.channel, author=interaction.user)
            ctx.cmd_name = "ready"
            await self.ready(ctx, captain)

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

        ctx = self.ih.get_new_context(self.match.channel)
        await disp.MATCH_CONFIRM.send(ctx, self.match.teams[0].captain.mention,
                                      self.match.teams[1].captain.mention, match=self.match.proxy)

        self.match.plugin_manager.on_teams_updated()

    @Process.public
    async def clear(self, ctx):
        self.ih.clean()
        await self.match.clean_all_auto()
        await disp.MATCH_CLEARED.send(ctx)

    @Process.public
    async def info(self):
        ctx = self.ih.get_new_context(self.match.channel)
        await disp.PK_SHOW_TEAMS.send(ctx, match=self.match.proxy)

    def on_team_ready(self, team, ready):
        team.captain.is_turn = not ready
        if ready:
            if self.is_first_round:
                self.match.base_selector.clean()
            self.match.command_factory.on_team_ready(team)
            self.match.plugin_manager.on_team_ready(team)
        team.on_team_ready(ready)

    def ready_check(self, team):
        other = self.match.teams[team.id - 1]
        # If other is_turn, then not ready
        # Else everyone ready
        if not other.captain.is_turn:
            self.ih.clean()
            self.match.ready_next_process()
            for tm in self.match.teams:
                tm.on_match_starting()
            return True
        return False

    @Process.public
    async def ready(self, ctx, captain):
        if not captain.is_turn:
            self.on_team_ready(captain.team, False)
            ctx = self.ih.get_new_context(ctx)
            await disp.MATCH_TEAM_UNREADY.send(ctx, captain.team.name, match=self.match.proxy)
            return
        if captain.is_turn:
            if self.match.check_validated:
                not_validated_players = accounts.get_not_validated_accounts(captain.team)
                if len(not_validated_players) != 0:
                    await disp.MATCH_PLAYERS_NOT_READY.send(ctx, captain.team.name,
                                                            " ".join(p.mention for p in not_validated_players))
                    return
            if self.match.check_offline:
                if self.getting_ready[captain.team.id]:
                    await disp.MATCH_GETTING_READY_DELAY.send(ctx)
                    return
                await disp.MATCH_GETTING_READY.send(ctx, captain.team.name)
                self.getting_ready[captain.team.id] = True
                try:
                    async with asyncio.timeout(15):
                        offline_players = await census.get_offline_players(captain.team)
                        if len(offline_players) != 0:
                            await disp.MATCH_PLAYERS_OFFLINE.send(ctx, captain.team.name,
                                                                  " ".join(p.mention for p in offline_players),
                                                                  "are" if len(offline_players) > 1 else "is",
                                                                  p_list=offline_players)
                            return
                except ApiNotReachable as e:
                    log.error(f"ApiNotReachable caught when checking online players: {e.url}")
                    await disp.API_READY_ERROR.send(ctx)
                except asyncio.TimeoutError:
                    log.error("TimeoutError caught when checking online players!")
                    await disp.API_READY_ERROR.send(ctx)
                finally:
                    self.getting_ready[captain.team.id] = False
            self.on_team_ready(captain.team, True)
            is_over = self.ready_check(captain.team)
            if not is_over:
                ctx = self.ih.get_new_context(ctx)
            await disp.MATCH_TEAM_READY.send(ctx, captain.team.name, match=self.match.proxy)
            if is_over:
                self.match.start_next_process()

    @Process.public
    async def try_remove_account(self, a_player, update=False):
        if a_player.account:
            await accounts.terminate_account(a_player)
            self.match.players_with_account.remove(a_player)
        if update:
            self.match.plugin_manager.on_teams_updated()

    @Process.public
    async def give_account(self, a_player, update=False):
        success = await accounts.give_account(a_player)
        if success:
            self.match.players_with_account.append(a_player)
            await accounts.send_account(self.match.channel, a_player)
            await disp.ACC_GIVING.send(self.match.channel, a_player.mention)
            if update:
                self.match.plugin_manager.on_teams_updated()
        else:
            await disp.ACC_NOT_ENOUGH.send(self.match.channel)
            await self.clear()

    @Process.public
    def get_current_context(self, ctx):
        return self.ih.get_new_context(ctx)

    @Process.public
    async def do_sub(self, subbed, force_player):
        ctx = self.ih.get_new_context(self.match.channel)
        new_player = await after_pick_sub(self.match, subbed.active, force_player, clean_subbed=False, ctx=ctx)
        if not new_player:
            return
        if not subbed.active.has_own_account:
            await self.try_remove_account(subbed.active)
        subbed.active.clean()
        if not new_player.active.has_own_account:
            await self.give_account(new_player.active)
        self.match.plugin_manager.on_teams_updated()

    @Process.public
    async def pick_status(self, ctx):
        await disp.PK_FACTION_INFO.send(ctx)
