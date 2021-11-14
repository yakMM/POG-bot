from .command import InstantiatedCommand, Command, picking_states
from match.classes import CaptainValidator
from match.common import after_pick_sub, get_check_captain
from match import MatchStatus

from display import AllStrings as disp, ContextWrapper

import modules.roles as roles
from classes import Player


class SubHandler(InstantiatedCommand):
    def __init__(self, obj):
        super().__init__(self, self.sub)
        self.sub_func = None
        self.factory = obj
        self.validator = None

    @property
    def match(self):
        return self.factory.match

    def on_start(self):
        self.validator = CaptainValidator(self.match)
        self.on_update()

        @self.validator.confirm
        async def do_sub(ctx, subbed, force_player=None):
            if self.sub_func:
                await self.sub_func(subbed, force_player)
            else:
                try:
                    ctx = self.match.get_process_attr('get_current_context')(ctx)
                except AttributeError:
                    pass
                await after_pick_sub(self.match, subbed.active, force_player, ctx=ctx)

    def on_clean(self, hard=False):
        if self.validator:
            self.validator.clean()
            if hard:
                self.validator = None

    def on_update(self):
        try:
            self.sub_func = self.match.get_process_attr('do_sub')
        except AttributeError:
            self.sub_func = None

    def on_team_ready(self, team):
        if self.validator and "subbed" in self.validator.kwargs:
            player = self.validator.kwargs["subbed"]
            if player.active and (player.active.team is team):
                self.validator.clean()

    @Command.command(*picking_states, MatchStatus.IS_CAPTAIN)
    async def sub(self, ctx, args):
        captain = None
        if not roles.is_admin(ctx.author):
            if self.match.status is MatchStatus.IS_CAPTAIN:
                await disp.SUB_ONLY_ADMIN.send(ctx)
                return
            captain = await get_check_captain(ctx, self.match, check_turn=False)
            if not captain:
                return

        if len(ctx.message.mentions) not in (1, 2):
            await disp.RM_MENTION_ONE.send(ctx)
            return

        subbed = Player.get(ctx.message.mentions[0].id)
        if not subbed:
            await disp.RM_NOT_IN_DB.send(ctx)
            return
        if not(subbed.match and subbed.match is self.match.proxy):
            await disp.SUB_NO.send(ctx)
            return
        if subbed.active and subbed.active.is_playing:
            subbed.active.team.captain.is_turn = True
            subbed.active.team.on_team_ready(False)

        # Can't have a swap command running at the same time
        self.factory.swap.on_clean()
        self.factory.bench.on_clean()

        if roles.is_admin(ctx.author):
            player = None
            if len(ctx.message.mentions) == 2:
                player = Player.get(ctx.message.mentions[1].id)
                if not player:
                    await disp.RM_NOT_IN_DB.send(ctx)
                    return
                elif player.match:
                    await disp.SUB_NO.send(ctx)
                    return
            await self.validator.force_confirm(ctx, subbed=subbed, force_player=player)
            return
        else:
            other_captain = self.match.teams[captain.team.id - 1].captain
            ctx = self.validator.arm(self.match.channel, captain, subbed=subbed)
            await disp.SUB_OK_CONFIRM.send(ctx, subbed.mention, other_captain.mention)
