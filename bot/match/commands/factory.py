from .command import Command, InstantiatedCommand, picking_states, captains_ok_states
from .sub_handler import SubHandler
from .swap_handler import SwapHandler
from .bench_handler import BenchHandler

from display import AllStrings as disp, ContextWrapper
from match import MatchStatus
import modules.config as cfg
import modules.roles as roles
from classes import Player
from match.common import check_faction, get_check_captain
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
        if self.match.status is MatchStatus.IS_WAITING and self.match.round_no > 0:
            await disp.MATCH_NO_COMMAND.send(ctx, ctx.command.name)
            return

        check_turn = self.match.status not in (MatchStatus.IS_BASING, MatchStatus.IS_WAITING)
        captain, msg = get_check_captain(ctx, self.match, check_turn=check_turn)
        if msg:
            await msg
            return

        if captain.team.is_playing:
            await disp.READY_NO_COMMAND.send(ctx)
            return

        try:
            await self.match.get_process_attr("pick")(ctx, captain, args)
        except AttributeError:
            # Check if faction is valid
            if await check_faction(ctx, args):
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

    @Command.has_help(disp.CAP_HELP)
    @Command.has_status("info")
    @Command.command(MatchStatus.IS_CAPTAIN)
    async def captain(self, ctx, args):
        match = self.match.proxy
        player = Player.get(ctx.author.id)
        if player is None or (player and not player.is_registered):
            # player not registered
            await disp.EXT_NOT_REGISTERED.send(ctx, cfg.channels["register"])
            return
        elif player.match is None:
            # if player not in match
            await disp.PK_NO_LOBBIED.send(ctx, cfg.channels["lobby"])
            return
        elif player.match.channel.id != match.channel.id:
            # if player not in the right match channel
            await disp.PK_WRONG_CHANNEL.send(ctx, player.match.channel.id)
            return
        if len(args) == 1:
            arg = args[0]
            if player.active and player.active.is_captain:
                await disp.CAP_ALREADY.send(ctx)
                return
            if arg in ("volunteer", "vol", "v"):
                await match.on_volunteer(player)
                return
            elif arg in ("accept", "acc", "a"):
                if not await match.on_answer(player, is_accept=True):
                    await disp.CAP_ACCEPT_NO.send(ctx)
                return
            elif arg in ("decline", "dec", "d"):
                if not await match.on_answer(player, is_accept=False):
                    await disp.CAP_DENY_NO.send(ctx)
                return
        await disp.WRONG_USAGE.send(ctx, ctx.command.name)

    @Command.command(MatchStatus.IS_WAITING)
    async def ready(self, ctx, args):
        match = self.match.proxy
        captain, msg = get_check_captain(ctx, match, check_turn=False)
        if msg:
            await msg
            return
        await match.ready(ctx, captain)

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

        if len(args) == 1 and (args[0] == "help" or args[0] == "h"):
            await disp.BASE_HELP.send(ctx)
            return

        # Check player status
        a_player = None
        if not roles.is_admin(ctx.author):
            a_player, msg = get_check_captain(ctx, self.match, check_turn=False)
            # If player doesn't have the proper status
            if msg:
                if len(args) == 0:
                    # If player just want to get base status, we give him
                    await self.match.base_selector.show_base_status(ctx)
                    # We will not use the message
                    msg.close()
                else:
                    # Else we display the error message
                    await msg
                return

        if self.match.teams[0].is_playing or self.match.teams[1].is_playing:
            if len(args) == 0:
                await self.match.base_selector.show_base_status(ctx)
            else:
                await disp.BASE_NO_READY.send(ctx)
            return

        await self.match.base_selector.process_request(ctx, a_player, args)

    @Command.command(*captains_ok_states, MatchStatus.IS_CAPTAIN)
    async def clear(self, ctx, args):
        match = self.match.proxy
        await disp.MATCH_CLEAR.send(ctx)
        await match.clear(ctx)

    @Command.command(*captains_ok_states, MatchStatus.IS_CAPTAIN, MatchStatus.IS_STARTING)
    async def info(self, ctx, args):
        match = self.match.proxy
        try:
            await match.info()
        except AttributeError:
            await disp.PK_SHOW_TEAMS.send(ctx, match=match)
