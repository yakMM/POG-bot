from .command import InstantiatedCommand, Command, picking_states
from match.classes import CaptainValidator
from match.common import get_check_captain
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
        async def do_bench(ctx, player, bench):
            team = player.team
            if bench and player.is_captain:
                if team.demote_captain():
                    await disp.CAP_NEW.send(ctx, team.captain.mention, team.name)
                else:
                    await disp.BENCH_ALL.send(ctx, player.mention)
                    return

            player.bench(bench)
            try:
                ctx = self.match.get_process_attr('get_current_context')(ctx)
            except AttributeError:
                pass
            if bench:
                await disp.BENCH_OK.send(ctx, player.mention, match=self.match.proxy)
            else:
                await disp.UNBENCH_OK.send(ctx, player.mention, match=self.match.proxy)

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
    async def bench(self, ctx, args, bench):
        captain = None
        if not roles.is_admin(ctx.author):
            captain = await get_check_captain(ctx, self.match, check_turn=False)
            if not captain:
                return

        if len(ctx.message.mentions) != 1:
            await disp.BENCH_MENTION.send(ctx)
            return

        p = Player.get(ctx.message.mentions[0].id)
        if not p:
            await disp.RM_NOT_IN_DB.send(ctx)
            return
        if not (p.match and p.active and p.match is self.match.proxy):
            await disp.BENCH_NO.send(ctx, p.mention)
            return
        if bench and p.active.is_benched:
            await disp.BENCH_ALREADY.send(ctx)
            return
        if not bench and not p.active.is_benched:
            await disp.BENCH_NOT.send(ctx)
            return
        if p.active.is_playing:
            p.active.team.captain.is_turn = True
            p.active.team.on_team_ready(False)

        player = p.active

        # Can't have another command running  at the same time
        self.factory.sub.on_clean()
        self.factory.swap.on_clean()

        if roles.is_admin(ctx.author):
            await self.validator.force_confirm(ctx, player=player, bench=bench)
            return
        else:
            other_captain = self.match.teams[captain.team.id - 1].captain
            ctx = self.validator.arm(self.match.channel, captain, player=player, bench=bench)
            if bench:
                await disp.BENCH_OK_CONFIRM.send(ctx, other_captain.mention)
            else:
                await disp.UNBENCH_OK_CONFIRM.send(ctx, other_captain.mention)
