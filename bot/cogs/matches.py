# @CHECK 2.0 features OK

from discord.ext import commands
from logging import getLogger

import modules.config as cfg
from modules.display import send, channelSend
from modules.tools import isAlNum
from modules.exceptions import ElementNotFound

from classes.players import TeamCaptain, ActivePlayer, PlayerStatus, getPlayer

from matches import getMatch
from modules.enumerations import MatchStatus, SelStatus
from modules.census import getOfflinePlayers
from classes.accounts import getNotReadyPlayers

log = getLogger(__name__)


class MatchesCog(commands.Cog, name='matches'):
    """
    Register cog, handle the commands in matches channels
    """

    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):  # Check if right channel
        return ctx.channel.id in cfg.channels['matches']

    """
    Commands:

    =pick
    =match
    =ready
    """

    @commands.command(aliases=['p'])
    @commands.guild_only()
    @commands.max_concurrency(number=1, wait=True)
    async def pick(self, ctx, *args):
        match = getMatch(ctx.channel.id)
        if len(args) == 1 and args[0] == "help":
            await send("PK_HELP", ctx)  # =p help shows the help
            return
        player = await _testPlayer(ctx, match)
        if player is None:
            return
        if match.status in (MatchStatus.IS_FREE, MatchStatus.IS_RUNNING):
            # Edge case, will happen very rarely if not never
            await send("MATCH_NOT_READY", ctx, ctx.command.name)
            return
        if match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
            await send("PK_OVER", ctx)  # Picking process is over
            return
        if player.status is PlayerStatus.IS_MATCHED:
            await send("PK_WAIT_FOR_PICK", ctx)  # Player is to be picked soon
            return
        aPlayer = player.active
        if isinstance(aPlayer, TeamCaptain):
            if match.status is MatchStatus.IS_MAPPING:
                await _map(ctx, aPlayer, args)  # map picking function
                return
            if match.status is MatchStatus.IS_WAITING:
                if match.roundNo == 1:
                    await _factionChange(ctx, aPlayer, args)
                    return
                await send("PK_OVER", ctx)  # Picking process is over
                return
            if aPlayer.isTurn:
                if match.status is MatchStatus.IS_PICKING:
                    await _pick(ctx, aPlayer, args)  # player picking function
                    return
                if match.status is MatchStatus.IS_FACTION:
                    # faction picking function
                    await _faction(ctx, aPlayer, args)
                    return
                await send("UNKNOWN_ERROR", ctx, "Unknown match state")  # Should never happen
                return
            await send("PK_NOT_TURN", ctx)
            return
        await send("PK_NOT_CAPTAIN", ctx)

    @commands.command(aliases=['m'])
    @commands.guild_only()
    async def match(self, ctx):  # list the current team comp
        match = getMatch(ctx.channel.id)
        if match.status not in (MatchStatus.IS_FREE, MatchStatus.IS_RUNNING):
            await send("PK_SHOW_TEAMS", ctx, match=match)
            return
        await send("MATCH_NO_MATCH", ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def resign(self, ctx):
        match = getMatch(ctx.channel.id)
        player = await _testPlayer(ctx, match)
        if player is None:
            return
        if match.status in (MatchStatus.IS_FREE, MatchStatus.IS_RUNNING):
            await send("MATCH_NOT_READY", ctx, ctx.command.name)
            return
        if match.status is not MatchStatus.IS_PICKING:
            await send("MATCH_NO_COMMAND", ctx, ctx.command.name)
            return
        if player.status is PlayerStatus.IS_MATCHED:
            await send("PK_WAIT_FOR_PICK", ctx)
            return
        aPlayer = player.active
        if not isinstance(aPlayer, TeamCaptain):
            await send("PK_NOT_CAPTAIN", ctx)
            return
        team = aPlayer.team
        if match.resign(aPlayer):
            await send("PK_RESIGNED", ctx, team.captain.mention, team.name)
        else:
            await send("PK_PICK_STARTED", ctx)

    @commands.command(aliases=['rdy'])
    @commands.guild_only()
    async def ready(self, ctx):  # when ready
        match = getMatch(ctx.channel.id)
        player = await _testPlayer(ctx, match)
        if player is None:
            return
        if match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
            # match not ready for this command
            await send("MATCH_ALREADY", ctx, ctx.command.name)
            return
        if match.status is not MatchStatus.IS_WAITING:
            # match not ready for this command
            await send("MATCH_NOT_READY", ctx, ctx.command.name)
            return
        # Getting the "active" version of the player (version when player is in matched, more data inside)
        aPlayer = player.active
        if isinstance(aPlayer, TeamCaptain):
            if aPlayer.isTurn:
                result = getNotReadyPlayers(aPlayer.team)
                if len(result) != 0:
                    await send("MATCH_PLAYERS_NOT_READY", ctx, aPlayer.team.name, " ".join(p.mention for p in result))
                    return
                result = await getOfflinePlayers(aPlayer.team)
                if len(result) != 0:
                    await send("MATCH_PLAYERS_OFFLINE", ctx, aPlayer.team.name, " ".join(p.mention for p in result), pList=result)
                    return
                match.onTeamReady(aPlayer.team)
                await send("MATCH_TEAM_READY", ctx, aPlayer.team.name, match=match)
                return
            aPlayer.isTurn = True
            await send("MATCH_TEAM_UNREADY", ctx, aPlayer.team.name, match=match)
            return
        await send("PK_NOT_CAPTAIN", ctx)

    @commands.command()
    @commands.guild_only()
    async def squittal(self, ctx):
        match = getMatch(ctx.channel.id)
        if match.status not in (MatchStatus.IS_WAITING, MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
            await send("MATCH_NOT_READY", ctx, ctx.command.name)
            return
        await send("SC_PLAYERS_STRING", ctx, "\n".join(tm.igString for tm in match.teams))


def setup(client):
    client.add_cog(MatchesCog(client))


async def _testPlayer(ctx, match):
    """ Test if the player is in position to issue a match command
        Returns the player object if yes, None if not
    """

    try:
        player = getPlayer(ctx.author.id)
    except ElementNotFound:
        # player not registered
        await send("EXT_NOT_REGISTERED", ctx,  cfg.channels["register"])
        return
    if player.status in (PlayerStatus.IS_NOT_REGISTERED, PlayerStatus.IS_REGISTERED, PlayerStatus.IS_LOBBIED):
        # if player not in match
        await send("PK_NO_LOBBIED", ctx,  cfg.channels["lobby"])
        return
    if player.match.id != match.id:
        # if player not in the right match channel
        await send("PK_WRONG_CHANNEL", ctx,  player.match.id)
        return
    return player


async def _pick(ctx, captain, args):
    """ Actual player pick function
    """

    if len(ctx.message.mentions) == 0:
        await send("PK_NO_ARG", ctx)  # no player mentioned
        return
    if len(ctx.message.mentions) > 1:
        await send("PK_TOO_MUCH", ctx)  # we want only one player mentioned
        return
    try:
        picked = getPlayer(ctx.message.mentions[0].id)
    except ElementNotFound:
        # player isn't even registered in the system...
        await send("PK_INVALID", ctx)
        return
    match = captain.match
    if picked.status is PlayerStatus.IS_MATCHED and picked.match.id == match.id:
        # this function return the next picker and triggers next step if everyone is already picked
        newPicker = match.pick(captain.team, picked)
        if match.status is MatchStatus.IS_FACTION:
            # Don't mention next picker
            await send("PK_OK_2", ctx, match=match)
            return
        await send("PK_OK", ctx, newPicker.mention, match=match)
        return
    await send("PK_INVALID", ctx)


async def _faction(ctx, captain, args):
    """ Actual faction pick function
    """
    isFaction = await _factionCheck(ctx, args)
    if not isFaction:
        return
    try:
        team = captain.team
        newPicker = captain.match.factionPick(team, args[0])
        if captain.match.status is not MatchStatus.IS_FACTION:
            await send("PK_FACTION_OK", ctx, team.name, cfg.factions[team.faction])  # faction picked
            return
        if newPicker == captain:
            # faction already picked
            await send("PK_FACTION_ALREADY", ctx)
            return
        await send("PK_FACTION_OK_NEXT", ctx, team.name, cfg.factions[team.faction], newPicker.mention)
    except KeyError:
        await send("PK_NOT_VALID_FACTION", ctx)

async def _factionChange(ctx, captain, args):
    isFaction = await _factionCheck(ctx, args)
    if not isFaction:
        return
    team = captain.team
    if not captain.isTurn:
        await send("PK_OVER_READY", ctx)
        return
    try:
        if captain.match.factionChange(team, args[0]):
            await send("PK_FACTION_CHANGED", ctx, team.name, cfg.factions[team.faction])
            return
        await send("PK_FACTION_ALREADY", ctx)
        return
    except KeyError:
        await send("PK_NOT_VALID_FACTION", ctx)

async def _map(ctx, captain, args):
    sel = captain.match.mapSelector
    match = captain.match
    if len(args) == 1 and args[0] == "confirm":
        if sel.status is not SelStatus.IS_SELECTED:
            await send("PK_NO_MAP", ctx)
            return
        if not captain.isTurn:
            await send("PK_NOT_TURN", ctx)
            return
        match.confirmMap()
        await send("MATCH_MAP_SELECTED", ctx, sel.map.name)
        return
    # Handle the actual map selection
    map = await sel.doSelectionProcess(ctx, args)
    if map is not None:
        newPicker = match.pickMap(captain)
        if newPicker != captain:
            await send("PK_MAP_OK_CONFIRM", ctx, sel.map.name, newPicker.mention)

async def _factionCheck(ctx, args):
    if len(args) != 1:
        # no faction is in two words...
        await send("PK_NOT_VALID_FACTION", ctx)
        return False
    if len(ctx.message.mentions) != 0:
        # Don't want a mentioned player
        await send("PK_FACTION_NOT_PLAYER", ctx)
        return False
    if not isAlNum(args[0]):
        # needs to be only alphanum chars
        await send("INVALID_STR", ctx, args[0])
        return False
    return True