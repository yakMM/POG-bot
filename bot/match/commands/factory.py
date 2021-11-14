from .command import Command, InstantiatedCommand, picking_states, captains_ok_states
from .sub_handler import SubHandler
from .swap_handler import SwapHandler
from .bench_handler import BenchHandler

from display import AllStrings as disp, ContextWrapper
from match import MatchStatus
import modules.config as cfg
import modules.roles as roles
from classes import Player
from match.common import check_faction, get_check_captain_sync, get_check_captain
from logging import getLogger

import modules.accounts_handler as accounts
import modules.census as census
from modules.asynchttp import ApiNotReachable


log = getLogger("pog_bot")

_external_commands = [SubHandler, SwapHandler, BenchHandler]


class MetaFactory(type):
    def __new__(mcs, c_name, c_base, c_dict, **kwargs):
        obj = type.__new__(mcs, c_name, c_base, c_dict)
        return obj

    def __init__(cls, c_name, c_base, c_dict):
        super().__init__(cls)
        cls.meta_commands = list()
        for func in c_dict.values():
            if isinstance(func, Command):
                cls.meta_commands.append(func)


class CommandFactory(metaclass=MetaFactory):
    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        obj.commands = dict()
        for command in obj.meta_commands:
            i_command = InstantiatedCommand(obj, command)
            obj.commands[i_command.name] = i_command
            setattr(obj, i_command.name, i_command)
        for command_cls in _external_commands:
            i_command = command_cls(obj)
            obj.commands[i_command.name] = i_command
            setattr(obj, i_command.name, i_command)
        return obj

    def __init__(self, match):
        self.match = match

    def on_status_update(self, status):
        for command in self.commands.values():
            command.on_status_update(status)

    def on_team_ready(self, team):
        for command in self.commands.values():
            command.on_team_ready(team)

    def on_clean(self):
        for command in self.commands.values():
            command.on_clean(hard=True)

    @Command.has_status("pick_status")
    @Command.command(*picking_states)
    async def pick(self, ctx, args):
        # If already second round
        if self.match.status is MatchStatus.IS_WAITING and self.match.round_no > 1:
            await disp.MATCH_NO_COMMAND.send(ctx, ctx.command.name)
            return

        check_turn = self.match.status not in (MatchStatus.IS_BASING, MatchStatus.IS_WAITING)
        captain = await get_check_captain(ctx, self.match, check_turn=check_turn)
        if not captain:
            return

        if captain.team.is_playing:
            captain.is_turn = True
            captain.team.on_team_ready(False)

        try:
            await self.match.get_process_attr('pick')(ctx, captain, args)
        except AttributeError:
            # Check if faction is valid
            if not await check_faction(ctx, args):
                # If error, return
                return

            # Get selected faction, get teams
            faction = cfg.i_factions[args[0].upper()]
            team = captain.team
            other = self.match.teams[team.id - 1]

            # Check if faction is already used, update faction
            if team.faction == faction:
                await disp.PK_FACTION_ALREADY.send(ctx, cfg.factions[faction])
            elif other.faction == faction:
                await disp.PK_FACTION_OTHER.send(ctx)
            else:
                team.faction = faction
                await disp.PK_FACTION_CHANGED.send(ctx, team.name, cfg.factions[faction])

            if self.match.status is MatchStatus.IS_WAITING:
                self.match.plugin_manager.on_teams_updated()

    @Command.command(MatchStatus.IS_WAITING)
    async def ready(self, ctx, args):
        captain = await get_check_captain(ctx, self.match, check_turn=False)
        if not captain:
            return
        await self.match.get_process_attr('ready')(ctx, captain)

    @Command.command(MatchStatus.IS_WAITING, MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING)
    async def squittal(self, ctx, args):
        if self.match.status is MatchStatus.IS_WAITING and \
                not (self.match.teams[0].is_playing and self.match.teams[0].is_playing):
            await disp.SC_PLAYERS_STRING_DISC.send(ctx, "\n".join(tm.ig_string for tm in self.match.teams))
        else:
            await disp.SC_PLAYERS_STRING.send(ctx, "\n".join(tm.ig_string for tm in self.match.teams))

    @Command.has_help(disp.BASE_HELP)
    @Command.command(*captains_ok_states, MatchStatus.IS_STARTING)
    async def base(self, ctx, args):
        bl = self.match.status in (MatchStatus.IS_PLAYING, MatchStatus.IS_STARTING)
        bl = bl or (self.match.status is MatchStatus.IS_WAITING and self.match.round_no > 1)
        if bl:
            if len(args) != 0:
                await disp.BASE_NO_CHANGE.send(ctx)
                return
            base = self.match.base
            await disp.BASE_SELECTED.send(ctx, base.name, base=base, is_booked=False)
            return

        # Check player status
        captain, msg = get_check_captain_sync(ctx, self.match, check_turn=False)
        # If player doesn't have the proper status
        if msg:
            if len(args) == 0:
                # If player just want to get base status, we give him
                await self.match.base_selector.show_base_status(ctx)
                msg.close()
                return
            elif not roles.is_admin(ctx.author):
                await msg
                return
            msg.close()

        if self.match.teams[0].is_playing or self.match.teams[1].is_playing:
            if len(args) == 0:
                await self.match.base_selector.show_base_status(ctx)
                return
            else:
                for tm in self.match.teams:
                    tm.captain.is_turn = True
                    tm.on_team_ready(False)

        await self.match.base_selector.process_request(ctx, captain, args)

    @Command.command(*captains_ok_states, MatchStatus.IS_CAPTAIN)
    async def clear(self, ctx, args):
        match = self.match
        await disp.MATCH_CLEAR.send(ctx)
        await match.get_process_attr('clear')(ctx)

    @Command.command(*captains_ok_states, MatchStatus.IS_CAPTAIN, MatchStatus.IS_STARTING)
    async def info(self, ctx, args):
        try:
            await self.match.get_process_attr('info')()
        except AttributeError:
            try:
                ctx = self.match.get_process_attr('get_current_context')(ctx)
            except AttributeError:
                pass
            await disp.PK_SHOW_TEAMS.send(ctx, match=self.match.proxy)
