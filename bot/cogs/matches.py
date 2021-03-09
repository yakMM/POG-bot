# @CHECK 2.0 features OK

from discord.ext import commands
from logging import getLogger

import modules.config as cfg
from display.strings import AllStrings as disp
from general.exceptions import ElementNotFound

from classes.players import Player

from match_process import Match
from general.enumerations import MatchStatus, SelStatus
from modules.census import get_offline_players
from modules.roles import is_admin
from classes.accounts import get_not_ready_players

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
    =resign
    =ready
    =squittal
    """

    @commands.command(aliases=['p'])
    @commands.guild_only()
    @commands.max_concurrency(number=1, wait=True)
    async def pick(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        if not await is_match_picking(ctx, match):
            return
        if len(args) == 0 or (len(args) == 1 and args[0] == "help"):
            # Display status
            await match.pick_status(ctx)
            return

        a_player, msg = _test_player(ctx, match)
        if msg:
            await msg
        else:
            await match.pick(ctx, a_player, args)

    @commands.command()
    @commands.guild_only()
    async def resign(self, ctx):
        match = Match.get(ctx.channel.id)
        if not await is_match_picking(ctx, match):
            return
        a_player, msg = _test_player(ctx, match)
        if msg:
            await msg
        else:
            team = a_player.team
            match.demote(a_player)
            await disp.PK_RESIGNED.send(ctx, team.captain.mention, team.name, match=match)

    @commands.command(aliases=['rdy'])
    @commands.guild_only()
    async def ready(self, ctx):  # when ready
        match = Match.get(ctx.channel.id)

        if match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
            # match not ready for this command
            await disp.MATCH_ALREADY.send(ctx, ctx.command.name)
            return
        if match.status is not MatchStatus.IS_WAITING:
            # match not ready for this command
            await disp.MATCH_NOT_READY.send(ctx, ctx.command.name)
            return

        a_player, msg = _test_player(ctx, match, check_turn=False)
        if msg:
            await msg
            return

        # Getting the "active" version of the player (version when player is in matched, more data inside)
        if a_player.is_turn:
            result = get_not_ready_players(a_player.team)
            if len(result) != 0:
                await disp.MATCH_PLAYERS_NOT_READY.send(ctx, a_player.team.name, " ".join(p.mention for p in result))
                return
            result = await get_offline_players(a_player.team)
            if len(result) != 0:
                await disp.MATCH_PLAYERS_OFFLINE.send(ctx, a_player.team.name, " ".join(p.mention for p in result), p_list=result)
                return
            match.on_team_ready(a_player.team)
            await disp.MATCH_TEAM_READY.send(ctx, a_player.team.name, match=match)
            return
        a_player.is_turn = True
        await disp.MATCH_TEAM_UNREADY.send(ctx, a_player.team.name, match=match)

    @commands.command()
    @commands.guild_only()
    async def squittal(self, ctx):
        match = Match.get(ctx.channel.id)
        if match.status not in (MatchStatus.IS_WAITING, MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
            await disp.MATCH_NOT_READY.send(ctx, ctx.command.name)
            return
        await disp.SC_PLAYERS_STRING.send(ctx, "\n".join(tm.ig_string for tm in match.teams))

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

        if len(args) == 1 and args[0]=="help":
            await disp.BASE_HELP.send(ctx)
            return

        # Check player status
        a_player, msg = _test_player(ctx, match, check_turn=False)

        # If player doesn't have the proper status
        if msg:
            # And is not admin
            if not is_admin(ctx.author):
                if len(args) == 0:
                    # If player just want to get base status, we give him
                    await match.base_selector.show_base_status(ctx)
                else:
                    # Else we display the error message
                    await msg
            # It's important to close the message in case we don't use it
            msg.close()
            return

        await match.base_selector.on_base_command(ctx, args)



def setup(client):
    client.add_cog(MatchesCog(client))


def _test_player(ctx, match, check_turn=True):
    """ Test if the player is in position to issue a match command
        Returns the player object if yes, None if not
    """
    msg = None
    a_player = None
    player = Player.get(ctx.author.id)
    if player is None:
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


async def is_match_picking(ctx, match):
    # Step 1: Test match status
    if match.status is MatchStatus.IS_FREE:
        # Match is not active
        await disp.MATCH_NO_MATCH.send(ctx, ctx.command.name)
        return False
    if not match.is_picking_allowed:
        # Match is not in right state
        await disp.MATCH_NO_COMMAND.send(ctx, ctx.command.name)
        return False
    return True



async def _faction_change(ctx, captain, args):
    is_faction = await _faction_check(ctx, args)
    if not is_faction:
        return
    team = captain.team
    if not captain.is_turn:
        await disp.PK_OVER_READY.send(ctx)
        return
    try:
        if captain.match.faction_change(team, args[0]):
            await disp.PK_FACTION_CHANGED.send(ctx, team.name, cfg.factions[team.faction])
            return
        await disp.PK_FACTION_ALREADY.send(ctx)
        return
    except KeyError:
        await disp.PK_NOT_VALID_FACTION.send(ctx)

async def _base(ctx, captain, args):
    sel = captain.match.base_selector
    match = captain.match
    if len(args) == 1 and args[0] == "confirm":
        if sel.status is not SelStatus.IS_SELECTED:
            await disp.PK_NO_BASE.send(ctx)
            return
        if not captain.is_turn:
            await disp.PK_NOT_TURN.send(ctx)
            return
        match.confirm_base()
        await disp.MATCH_BASE_SELECTED.send(ctx, sel.base.name, sel=sel)
        return
    # Handle the actual base selection
    base = await sel.do_selection_process(ctx, args)
    if base:
        new_picker = match.pick_base(captain)
        await sel.wait_confirm(ctx, new_picker)
        if sel.is_booked:
            await disp.BASE_BOOKED.send(ctx, new_picker.mention, sel.base.name)
