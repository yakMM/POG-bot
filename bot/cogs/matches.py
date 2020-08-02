from discord.ext import commands
import discord

import modules.config as cfg
from modules.display import send, channelSend
from modules.tools import isAlNum
from modules.exceptions import ElementNotFound

from classes.players import TeamCaptain, ActivePlayer, PlayerStatus, getPlayer
from classes.maps import MapSelection

from matches import getMatch
from modules.enumerations import MatchStatus, SelStatus

globId=0

class MatchesCog(commands.Cog, name='matches'):
    """
    Register cog, handle the commands in matches channels
    """


    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('Matches Cog is online')
        return # we don't display a message on each restart
        try:
            for id in cfg.discord_ids["matches"]:
                await channelSend("CHANNEL_INIT", id, id)
        except AttributeError:
            raise UnexpectedError("Invalid channel id!")

    async def cog_check(self, ctx): # Check if right channel
        return ctx.channel.id in cfg.discord_ids['matches']
    
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
        if len(args)==1 and args[0].lower()=="help":
            await send("PK_HELP", ctx) # =p help shows the help
            return
        player = await _testPlayer(ctx, match)
        if player == None:
            return
        if match.status in (MatchStatus.IS_FREE, MatchStatus.IS_RUNNING):
            await send("MATCH_NOT_READY", ctx, ctx.command.name) # Edge case, will happen very rarely if not never
            return
        if match.status in (MatchStatus.IS_WAITING, MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
            await send("PK_OVER", ctx) # Picking process is over
            return
        if player.status == PlayerStatus.IS_MATCHED:
            await send("PK_WAIT_FOR_PICK", ctx) # Player is to be picked soon
            return
        aPlayer = player.active
        if isinstance(aPlayer, TeamCaptain):
            if match.status == MatchStatus.IS_MAPPING:
                    await _map(ctx, aPlayer, args) # map picking function
                    return
            if aPlayer.isTurn:
                if match.status == MatchStatus.IS_PICKING:
                    await _pick(ctx, aPlayer, args) # player picking function
                    return
                if match.status == MatchStatus.IS_FACTION:
                    await _faction(ctx, aPlayer, args) # faction picking function
                    return
                await send("UNKNOWN_ERROR", ctx, "Unknown match state")
                return
            await send("PK_NOT_TURN", ctx)
            return
        await send("PK_NOT_CAPTAIN", ctx)

    @commands.command(aliases=['m'])
    @commands.guild_only()
    async def match(self, ctx): # list the current team comp
        match = getMatch(ctx.channel.id)
        if match.status not in (MatchStatus.IS_FREE, MatchStatus.IS_RUNNING):
            await send("PK_SHOW_TEAMS", ctx, match=match)
            return
        await send("MATCH_NO_MATCH", ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def ready(self, ctx): # when ready
        match = getMatch(ctx.channel.id)
        player = await _testPlayer(ctx, match)
        if player == None:
            return
        if match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
            await send("MATCH_ALREADY", ctx, ctx.command.name) # match not ready for this command
            return
        if match.status != MatchStatus.IS_WAITING:
            await send("MATCH_NOT_READY", ctx, ctx.command.name) # match not ready for this command
            return
        aPlayer = player.active # Getting the "active" version of the player (version when player is in matched, more data inside)
        if isinstance(aPlayer, TeamCaptain):
            if aPlayer.isTurn:
                result = aPlayer.match.onTeamReady(aPlayer.team)
                if result != None:
                    await send("MATCH_PLAYERS_NOT_READY", ctx, aPlayer.team.name, " ".join(result))
                    return
                await send("MATCH_TEAM_READY", ctx, aPlayer.team.name, match=match)
                return
            aPlayer.isTurn = True
            await send("MATCH_TEAM_UNREADY", ctx, aPlayer.team.name, match=match)
            return
        await send("PK_NOT_CAPTAIN", ctx)

def setup(client):
    client.add_cog(MatchesCog(client))

async def _testPlayer(ctx, match):
    """ Test if the player is in position to issue a match command
        Returns the player object if yes, None if not
    """

    try:
        player = getPlayer(ctx.author.id)
    except ElementNotFound:
        await send("EXT_NOT_REGISTERED", ctx,  cfg.discord_ids["register"]) # player not registered
        return
    if player.status in (PlayerStatus.IS_NOT_REGISTERED, PlayerStatus.IS_REGISTERED, PlayerStatus.IS_LOBBIED):
        await send("PK_NO_LOBBIED", ctx,  cfg.discord_ids["lobby"]) # if player not in match
        return
    if player.match.id != match.id:
        await send("PK_WRONG_CHANNEL", ctx,  player.match.id) # if player not in the right match channel
        return
    return player

async def _pick(ctx, captain, args):
    """ Actual player pick function
    """
    
    if len(ctx.message.mentions)==0:
        await send("PK_NO_ARG", ctx) # no player mentioned
        return
    if len(ctx.message.mentions)>1:
        await send("PK_TOO_MUCH", ctx) # we want only one player mentioned
        return
    try:
        picked = getPlayer(ctx.message.mentions[0].id)
    except ElementNotFound:
        await send("PK_INVALID", ctx) # player isn't even registered in the system...
        return
    match = captain.match
    if picked.status == PlayerStatus.IS_MATCHED and picked.match.id == match.id:
        newPicker = match.pick(captain.team, picked) # this function return the next picker and triggers next step if everyone is already picked
        if match.status == MatchStatus.IS_FACTION:
            await send("PK_OK_2", ctx, match=match) # Don't mention next picker
            return
        await send("PK_OK", ctx, newPicker.mention, match=match)
        return
    await send("PK_INVALID", ctx)

async def _faction(ctx, captain, args):
    """ Actual faction pick function
    """
    if len(args)!=1:
        await send("PK_NOT_VALID_FACTION", ctx) # no faction is in two words...
        return
    if len(ctx.message.mentions)!=0:
        await send("PK_FACTION_NOT_PLAYER", ctx) # Don't want a mentioned player
        return
    if not isAlNum(args[0]):
        await send("INVALID_STR",ctx , args[0]) # needs to be only alphanum chars
        return
    try:
        team = captain.team
        newPicker = captain.match.factionPick(team, args[0].upper())
        if captain.match.status != MatchStatus.IS_FACTION:
            await send("PK_FACTION_OK", ctx, team.name, cfg.factions[team.faction]) # faction picked
            return
        if newPicker == captain:
            await send("PK_FACTION_ALREADY", ctx, newPicker.mention) # faction already picked
            return
        await send("PK_FACTION_OK_NEXT", ctx, team.name, cfg.factions[team.faction], newPicker.mention)
    except KeyError:
        await send("PK_NOT_VALID_FACTION", ctx)


async def _map(ctx, captain, args):
    sel = captain.match.mapSelector
    match = captain.match
    if len(args) == 1 and args[0].lower() == "confirm":
        if sel.status != SelStatus.IS_SELECTED:
            await send("PK_NO_MAP", ctx)
            return
        if not captain.isTurn:
            await send("PK_NOT_TURN", ctx)
            return
        match.confirmMap()
        await send("MATCH_MAP_SELECTED", ctx, sel.map.name)
        return
    await sel.doSelectionProcess(ctx, args) # Handle the actual map selection
    newPicker = match.pickMap(captain)
    if newPicker != captain:
        await send("PK_MAP_OK_CONFIRM", ctx, sel.map.name, newPicker.mention )