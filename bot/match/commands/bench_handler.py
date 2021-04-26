from .command import InstantiatedCommand, Command, picking_states
from match.classes import CaptainValidator
from match.common import after_pick_sub, get_check_captain
from match import MatchStatus

from display import AllStrings as disp, ContextWrapper

import modules.roles as roles
from classes import Player


class BenchHandler(InstantiatedCommand):
    def __init__(self, obj):
        super().__init__(self, self.bench)
        self.validator = None
        self.factory = obj

    @property
    def match(self):
        return self.factory.match

    def on_start(self):
        self.validator = CaptainValidator(self.match)

        @self.validator.confirm
        async def do_bench(ctx, p1, p2):
            p1.team.remove(p1)
            p2.team.remove(p2)
            for p in (p1, p2):
                if not p.has_own_account:
                    try:
                        await self.match.remove_account(p)
                    except AttributeError:
                        pass
            await disp.BENCH_OK.send(self.match.channel, p1.mention, p2.mention, match=self.match.proxy)

    def on_clean(self, hard=False):
        if self.validator:
            self.validator.clean()
            if hard:
                self.validator = None

    def on_team_ready(self, team):
        if self.validator:
            self.validator.clean()

    @Command.command(*picking_states)
    async def bench(self, ctx, args):
        captain = None
        if not roles.is_admin(ctx.author):
            captain, msg = get_check_captain(ctx, self.match, check_turn=False)
            if msg:
                await msg
                return

            if await self.validator.check_message(ctx, captain, args):
                return

        if len(ctx.message.mentions) != 2:
            await disp.BENCH_MENTION_2.send(ctx)
            return

        players = list()
        for mention in ctx.message.mentions:
            p = Player.get(mention.id)
            if not p:
                await disp.RM_NOT_IN_DB.send(ctx)
                return
            if not (p.match and p.active and p.match.id == self.match.id):
                await disp.BENCH_NO.send(ctx, p.mention)
                return
            if p.active.is_captain:
                await disp.RM_CAP.send(ctx, p.mention)
                return
            if p.active.is_playing:
                await disp.BENCH_RDY.send(ctx)
                return
            players.append(p.active)

        if players[0].team is players[1].team:
            await disp.BENCH_SAME_TEAM.send(ctx)
            return

        # Can't have another command running  at the same time
        self.factory.sub.on_clean()
        self.factory.swap.on_clean()

        if roles.is_admin(ctx.author):
            await self.validator.force_confirm(ctx, p1=players[0], p2=players[1])
            return
        else:
            other_captain = self.match.teams[captain.team.id - 1].captain
            msg = await disp.BENCH_OK_CONFIRM.send(self.match.channel, other_captain.mention)
            await self.validator.wait_valid(captain, msg, p1=players[0], p2=players[1])
