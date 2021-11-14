from .command import InstantiatedCommand, Command, picking_states
from match.classes import CaptainValidator
from match.common import get_check_captain
from match import MatchStatus

from display import AllStrings as disp, ContextWrapper

import modules.roles as roles
from classes import Player


class SwapHandler(InstantiatedCommand):
    def __init__(self, obj):
        super().__init__(self, self.swap)
        self.validator = None
        self.factory = obj

    @property
    def match(self):
        return self.factory.match

    def on_start(self):
        self.validator = CaptainValidator(self.match)

        @self.validator.confirm
        async def do_swap(ctx, p_1, p_2):
            team1 = p_1.team
            team2 = p_2.team
            team1.swap_player(p_1, p_2)
            team2.swap_player(p_2, p_1)
            p_1.change_team(team2)
            p_2.change_team(team1)

            try:
                ctx = self.match.get_process_attr('get_current_context')(ctx)
            except AttributeError:
                pass
            await disp.SWAP_OK.send(ctx, p_1.mention, p_2.mention, match=self.match.proxy)

            if self.match.status is MatchStatus.IS_WAITING:
                self.match.plugin_manager.on_teams_updated()

    def on_clean(self, hard=False):
        if self.validator:
            self.validator.clean()
            if hard:
                self.validator = None

    def on_team_ready(self, team):
        if self.validator:
            self.validator.clean()

    @Command.command(*picking_states)
    async def swap(self, ctx, args):
        captain = None
        if not roles.is_admin(ctx.author):
            captain = await get_check_captain(ctx, self.match, check_turn=False)
            if not captain:
                return

        if len(ctx.message.mentions) != 2:
            await disp.SWAP_MENTION_2.send(ctx)
            return

        players = list()
        for mention in ctx.message.mentions:
            p = Player.get(mention.id)
            if not p:
                await disp.RM_NOT_IN_DB.send(ctx)
                return
            if not(p.match and p.active and p.match is self.match.proxy):
                await disp.SWAP_NO.send(ctx, p.mention)
                return
            if p.active.is_playing:
                p.active.team.captain.is_turn = True
                p.active.team.on_team_ready(False)
            players.append(p.active)

        if players[0].team is players[1].team:
            await disp.SWAP_SAME_TEAM.send(ctx)
            return

        # Can't have a sub command running  at the same time
        self.factory.sub.on_clean()
        self.factory.bench.on_clean()

        if roles.is_admin(ctx.author):
            await self.validator.force_confirm(ctx, p_1=players[0], p_2=players[1])
            return
        else:
            other_captain = self.match.teams[captain.team.id - 1].captain
            ctx = self.validator.arm(self.match.channel, captain, p_1=players[0], p_2=players[1])
            await disp.SWAP_OK_CONFIRM.send(ctx, other_captain.mention)
