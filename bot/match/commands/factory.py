from .command import Command, InstantiatedCommand, picking_states
from .sub_handler import SubHandler

from display import AllStrings as disp, ContextWrapper
from match import MatchStatus
import modules.config as cfg
import modules.roles as roles
from classes import Player
from match.common import check_faction, get_check_captain

_external_commands = [SubHandler]


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

    async def on_status_update(self, status):
        for command in self.commands.values():
            await command.on_status(status)

    @Command.has_status("pick_status")
    @Command.command(*picking_states)
    async def pick(self, ctx, args):
        captain, msg = get_check_captain(ctx, self.match)
        if msg:
            await msg
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
        a_player, msg = get_check_captain(ctx, match, check_turn=False)
        if msg:
            await msg
            return
        await match.team_ready(ctx, a_player)

    @Command.command(MatchStatus.IS_WAITING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT)
    async def squittal(self, ctx, args):
        if self.match.status is MatchStatus.IS_WAITING:
            await disp.SC_PLAYERS_STRING_DISC.send(ctx, "\n".join(tm.ig_string for tm in self.match.teams))
        else:
            await disp.SC_PLAYERS_STRING.send(ctx, "\n".join(tm.ig_string for tm in self.match.teams))

    @Command.has_help(disp.BASE_HELP)
    @Command.command(MatchStatus.IS_WAITING, MatchStatus.IS_PLAYING, MatchStatus.IS_BASING, MatchStatus.IS_PICKING,
                     MatchStatus.IS_FACTION, MatchStatus.IS_RESULT)
    async def base(self, ctx, args):
        if self.match.status in (MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
            if len(args) != 0:
                await disp.BASE_NO_CHANGE.send(ctx)
                return
            await disp.BASE_SELECTED.send(ctx, base=self.match.base, is_booked=False)
            return

        if len(args) == 1 and args[0] == "help":
            await disp.BASE_HELP.send(ctx)
            return

        # Check player status
        a_player, msg = get_check_captain(ctx, self.match, check_turn=False)

        # If player doesn't have the proper status
        if msg:
            # And is not admin
            if not roles.is_admin(ctx.author):
                if len(args) == 0:
                    # If player just want to get base status, we give him
                    await self.match.base_selector.show_base_status(ctx)
                    # We will not use the message
                    msg.close()
                else:
                    # Else we display the error message
                    await msg
                return
            # It's important to close the message in case we don't use it
            msg.close()
        await self.match.base_selector.process_request(ctx, a_player, args)
