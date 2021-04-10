from .command import InstantiatedCommand, Command, picking_states
from match.classes import CaptainValidator
from match.common import after_pick_sub, get_check_captain
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

    def start(self):
        self.validator = CaptainValidator(self.match)

        @self.validator.confirm
        async def do_swap(ctx, p_1, p_2):
            team1 = p_1.team
            team2 = p_2.team
            team1.swap_player(p_1, p_2)
            team2.swap_player(p_2, p_1)
            p_1.change_team(team2)
            p_2.change_team(team1)
            await disp.SWAP_OK.send(self.match.channel, p_1.mention, p_2.mention, match=self.match.proxy)

    def stop(self):
        self.validator.clean()

    def on_team_ready(self, team):
        self.stop()

    @Command.command(*picking_states)
    async def swap(self, ctx, args):
        captain = None
        if not roles.is_admin(ctx.author):
            captain, msg = get_check_captain(ctx, self.match, check_turn=False)
            if msg:
                await msg
                return

            if await self.validator.check_message(ctx, captain, args):
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
            if not(p.match and p.active and p.match.id == self.match.id):
                await disp.SWAP_NO.send(ctx, p.mention)
                return
            if p.active.is_captain:
                await disp.SWAP_CAP.send(ctx, p.mention)
                return
            if p.active.is_playing:
                await disp.SWAP_RDY.send(ctx)
                return
            players.append(p.active)

        if players[0].team is players[1].team:
            await disp.SWAP_SAME_TEAM.send(ctx)
            return

        # Can't have a sub command running  at the same time
        await self.factory.sub.stop()

        if roles.is_admin(ctx.author):
            await self.validator.force_confirm(ctx, p_1=players[0], p_2=players[1])
            return
        else:
            other_captain = self.match.teams[captain.team.id - 1].captain
            msg = await disp.SWAP_OK_CONFIRM.send(self.match.channel, other_captain.mention)
            await self.validator.wait_valid(captain, msg, p_1=players[0], p_2=players[1])
