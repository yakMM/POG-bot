# @CHECK 2.0 features OK

from discord.ext import commands
from logging import getLogger

import modules.config as cfg
from display.strings import AllStrings as disp

import classes

from match_process.match import Match
from match_process import MatchStatus
from modules.roles import is_admin

log = getLogger("pog_bot")


class MatchesCog(commands.Cog, name='matches'):
    """
    Matches cog, handle the user commands in matches channels
    """

    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):
        # Check if right channel
        return ctx.channel.id in cfg.channels['matches']

    """
    Commands:

    =pick
    =captain
    =sub
    =ready
    =squittal
    """

    @commands.command(aliases=['p'])
    @commands.guild_only()
    async def pick(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        if match.status is MatchStatus.IS_FREE:
            # Match is not active
            await disp.MATCH_NO_MATCH.send(ctx, ctx.command.name)
            return
        if not match.is_picking_allowed:
            await disp.MATCH_NO_COMMAND.send(ctx, ctx.command.name)
            return
        if len(args) == 0 or (len(args) == 1 and args[0] == "help"):
            # Display status
            await match.pick_status(ctx)
            return

        a_player, msg = _get_check_captain(ctx, match)
        if msg:
            await msg
            return

        await match.pick(ctx, a_player, args)

    @commands.command(aliases=['c', 'cap'])
    @commands.guild_only()
    async def captain(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        if match.status is MatchStatus.IS_FREE:
            # Match is not active
            await disp.MATCH_NO_MATCH.send(ctx, ctx.command.name)
            return
        if match.status is not MatchStatus.IS_CAPTAIN:
            await disp.MATCH_NO_COMMAND.send(ctx, ctx.command.name)
            return
        if len(args) == 1 and args[0] == "help":
            await disp.CAP_HELP.send(ctx)
            return
        elif len(args) == 0:
            await match.info()
            return
        player = classes.Player.get(ctx.author.id)
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

    @commands.command()
    @commands.guild_only()
    async def sub(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        # Check match status
        if match.status is MatchStatus.IS_FREE:
            await disp.MATCH_NO_MATCH.send(ctx, ctx.command.name)
            return
        elif not match.is_picking_allowed:
            await disp.MATCH_NO_COMMAND.send(ctx, ctx.command.name)
            return

        captain, msg = _get_check_captain(ctx, match, check_turn=False)
        if msg:
            if is_admin(ctx.author):
                msg.close()
            else:
                await msg
                return

        # display is handled in the sub method, nothing to display here
        await match.sub_request(ctx, captain, args)

    @commands.command(aliases=['rdy'])
    @commands.guild_only()
    async def ready(self, ctx):  # when ready
        match = Match.get(ctx.channel.id)
        if match.status is MatchStatus.IS_FREE:
            # Match is not active
            await disp.MATCH_NO_MATCH.send(ctx, ctx.command.name)
            return
        if match.status in (MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
            # match not ready for this command
            await disp.MATCH_ALREADY.send(ctx, ctx.command.name)
            return
        if match.status is not MatchStatus.IS_WAITING:
            await disp.MATCH_NO_COMMAND.send(ctx, ctx.command.name)
            return

        a_player, msg = _get_check_captain(ctx, match, check_turn=False)
        if msg:
            await msg
            return

        await a_player.match.team_ready(ctx, a_player)

    @commands.command()
    @commands.guild_only()
    async def squittal(self, ctx):
        match = Match.get(ctx.channel.id)
        if match.next_status is MatchStatus.IS_WAITING:
            await disp.SC_PLAYERS_STRING_DISC.send(ctx, "\n".join(tm.ig_string for tm in match.teams))
        elif not match.is_picking_allowed:
            await disp.SC_PLAYERS_STRING.send(ctx, "\n".join(tm.ig_string for tm in match.teams))
        else:
            await disp.MATCH_NOT_READY.send(ctx, ctx.command.name)

    @commands.command(aliases=['b', 'map'])
    @commands.guild_only()
    async def base(self, ctx, *args):
        match = Match.get(ctx.channel.id)

        # Check match status
        if match.status is MatchStatus.IS_FREE:
            await disp.MATCH_NO_MATCH.send(ctx, ctx.command.name)
            return
        elif match.status is MatchStatus.IS_RUNNING:
            await disp.MATCH_NO_COMMAND.send(ctx, ctx.command.name)
            return
        elif not match.is_picking_allowed:
            if len(args) != 0:
                await disp.BASE_NO_CHANGE.send(ctx)
                return
            await disp.BASE_SELECTED.send(ctx, base=match.base, is_booked=False)
            return

        if len(args) == 1 and args[0] == "help":
            await disp.BASE_HELP.send(ctx)
            return

        # Check player status
        a_player, msg = _get_check_captain(ctx, match, check_turn=False)

        # If player doesn't have the proper status
        if msg:
            # And is not admin
            if not is_admin(ctx.author):
                if len(args) == 0:
                    # If player just want to get base status, we give him
                    await match.base_selector.show_base_status(ctx)
                    # We will not use the message
                    msg.close()
                else:
                    # Else we display the error message
                    await msg
                return
            # It's important to close the message in case we don't use it
            msg.close()
        await match.base_selector.process_request(ctx, a_player, args)


def setup(client):
    client.add_cog(MatchesCog(client))


def _get_check_captain(ctx, match, check_turn=True):
    """ Test if the player is in position to issue a match command
        Returns the player object if yes, None if not
    """
    msg = None
    a_player = None
    player = classes.Player.get(ctx.author.id)
    if player is None or (player and not player.is_registered):
        # player not registered
        msg = disp.EXT_NOT_REGISTERED.send(ctx, cfg.channels["register"])
    elif player.match is None:
        # if player not in match
        msg = disp.PK_NO_LOBBIED.send(ctx, cfg.channels["lobby"])
    elif player.match.channel.id != match.channel.id:
        # if player not in the right match channel
        msg = disp.PK_WRONG_CHANNEL.send(ctx, player.match.channel.id)
    elif player.active is None:
        # Player is in the pick list
        msg = disp.PK_WAIT_FOR_PICK.send(ctx)
    elif not player.active.is_captain:
        # Player is not team captain
        msg = disp.PK_NOT_CAPTAIN.send(ctx)
    elif check_turn and not player.active.is_turn:
        # Not player's turn
        msg = disp.PK_NOT_TURN.send(ctx)
    else:
        a_player = player.active
    return a_player, msg
