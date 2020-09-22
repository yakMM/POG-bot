from discord.ext import commands
from logging import getLogger
from datetime import datetime as dt

import modules.config as cfg
from modules.enumerations import SelStatus, MatchStatus, PlayerStatus
from modules.display import send, channelSend
from modules.exceptions import ElementNotFound, DatabaseError
from modules.database import removePlayer as dbRemove
from modules.loader import lockAll, unlockAll, isAllLocked
from modules.roles import forceInfo, roleUpdate, isAdmin, permsMuted, channelFreeze
from modules.census import getOfflinePlayers

from classes.players import removePlayer, getPlayer, Player, TeamCaptain

from matches import clearLobby, getMatch, getAllNamesInLobby, removeFromLobby, isLobbyStuck, addToLobby, getAllIdsInLobby


log = getLogger(__name__)


class AdminCog(commands.Cog, name='admin'):
    """
    Register cog, handle the admin commands
    """

    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):
        return isAdmin(ctx.author)

    """
    Admin Commands

    =clear (clear lobby or match)
    =map (select a map)

    """

    @commands.command()
    @commands.guild_only()
    async def clear(self, ctx):
        if ctx.channel.id == cfg.channels["lobby"]:  # clear lobby
            if clearLobby():
                await send("LB_CLEARED", ctx, namesInLobby=getAllNamesInLobby())
                return
            await send("LB_EMPTY", ctx)
            return
        # clear a match channel
        if ctx.channel.id in cfg.channels["matches"]:
            match = getMatch(ctx.channel.id)
            if match.status is MatchStatus.IS_FREE:
                await send("MATCH_NO_MATCH", ctx, ctx.command.name)
                return
            if match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_RESULT, MatchStatus.IS_RUNNING):
                await send("MATCH_NO_COMMAND", ctx, ctx.command.name)
                return
            await send("MATCH_CLEAR", ctx)
            await match.clear()
            await send("MATCH_CLEARED", ctx)
            return
        await send("WRONG_CHANNEL_2", ctx, ctx.command.name, f"<#{ctx.channel.id}>")

    @commands.command()
    @commands.guild_only()
    async def map(self, ctx, *args):
        channelId = ctx.channel.id
        if channelId not in cfg.channels["matches"]:
            await send("WRONG_CHANNEL", ctx, ctx.command.name, " channels " + ", ".join(f'<#{id}>' for id in cfg.channels["matches"]))
            return
        match = getMatch(ctx.channel.id)
        if match.status is MatchStatus.IS_FREE:
            await send("MATCH_NO_MATCH", ctx, ctx.command.name)
            return
        if match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT, MatchStatus.IS_RUNNING):
            await send("MATCH_NO_COMMAND", ctx, ctx.command.name)
            return
        sel = match.mapSelector
        # Handle the actual map selection
        await sel.doSelectionProcess(ctx, args)
        if sel.status is SelStatus.IS_SELECTED:
            match.confirmMap()
            await send("MATCH_MAP_SELECTED", ctx, sel.map.name)

    @commands.command()
    @commands.guild_only()
    async def unregister(self, ctx):
        player = await _removeChecks(ctx, cfg.channels["register"])
        if player is None:
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            removeFromLobby(player)
            await channelSend("RM_LOBBY", cfg.channels["lobby"], player.mention, namesInLobby=getAllNamesInLobby())
        if player.status in (PlayerStatus.IS_REGISTERED, PlayerStatus.IS_NOT_REGISTERED):
            try:
                await dbRemove(player)
            except DatabaseError:
                pass  # ignored if not yet in db
            await forceInfo(player.id)
            removePlayer(player)
            await send("RM_OK", ctx)
            return
        await send("RM_IN_MATCH", ctx)
    
    @commands.command()
    @commands.guild_only()
    async def remove(self, ctx):
        player = await _removeChecks(ctx, cfg.channels["lobby"])
        if player is None:
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            removeFromLobby(player)
            await channelSend("RM_LOBBY", cfg.channels["lobby"], player.mention, namesInLobby=getAllNamesInLobby())
            return
        await send("RM_NOT_LOBBIED", ctx)
    
    @commands.command()
    @commands.guild_only()
    async def demote(self, ctx):
        player = await _removeChecks(ctx, cfg.channels["matches"])
        if player is None:
            return
        if player.status is not PlayerStatus.IS_PICKED:
            await send("RM_DEMOTE_NO", ctx)
            return
        match = getMatch(ctx.channel.id)
        if player.match.id != match.id:
            await send("PK_WRONG_CHANNEL", ctx,  player.match.id)
            return
        aPlayer = player.active
        if not isinstance(aPlayer, TeamCaptain):
            await send("RM_DEMOTE_NO", ctx)
            return
        team = aPlayer.team
        if match.resign(aPlayer):
            await send("RM_DEMOTE_OK", ctx, team.captain.mention, team.name)
        else:
            await send("RM_DEMOTE_PICKING", ctx)

    @commands.command()
    @commands.guild_only()
    async def lobby(self, ctx, *args):
        if ctx.channel.id != cfg.channels["lobby"]:
            await send("WRONG_CHANNEL", ctx, ctx.command.name, f'<#{cfg.channels["lobby"]}>')
            return
        if len(args)>0 and args[0] == "restore":
            for pId in args[1:]:
                try:
                    player = getPlayer(int(pId))
                    if not isLobbyStuck() and player.status is PlayerStatus.IS_REGISTERED:
                        addToLobby(player)
                except (ElementNotFound, ValueError):
                    pass
            await send("LB_QUEUE", ctx, namesInLobby=getAllNamesInLobby())
            return
        if len(args)>0 and args[0] == "get":
            await send("LB_GET", ctx, " ".join(getAllIdsInLobby()))
            return
        await send("WRONG_USAGE", ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def timeout(self, ctx, *args):
        if len(args) == 0:
            await send("RM_TIMEOUT_HELP", ctx)
            return
        if len(args) == 1 and args[0] == "help":
            await send("RM_TIMEOUT_HELP", ctx)
            return
        if len(ctx.message.mentions) != 1:
            await send("RM_MENTION_ONE", ctx)
            return
        try:
            player = getPlayer(ctx.message.mentions[0].id)
        except ElementNotFound:
            # player isn't even registered in the system...
            player = Player(ctx.message.mentions[0].id, ctx.message.mentions[0].name)
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            removeFromLobby(player)
            await channelSend("RM_LOBBY", cfg.channels["lobby"], player.mention, namesInLobby=getAllNamesInLobby())
        if player.status not in (PlayerStatus.IS_REGISTERED, PlayerStatus.IS_NOT_REGISTERED):
            await send("RM_IN_MATCH", ctx)
            return
        if len(args) == 1:
            if player.isTimeout:
                await send("RM_TIMEOUT_INFO", ctx, dt.utcfromtimestamp(player.timeout).strftime("%Y-%m-%d %H:%M UTC"))
                return
            await roleUpdate(player)
            await permsMuted(False, player.id)
            await send("RM_TIMEOUT_NO", ctx)
            return
        # =timeout @player remove
        if len(args) == 2 and args[1] == 'remove':
            if not player.isTimeout:
                await send("RM_TIMEOUT_ALREADY", ctx)
                return
            player.timeout = 0
            await player.dbUpdate("timeout")
            await send("RM_TIMEOUT_FREE", ctx, player.mention)
            await roleUpdate(player)
            await permsMuted(False, player.id)
            return
        # Check if command is correct (=timeout @player 12 d)
        if len(args) != 3:
            await send("RM_TIMEOUT_INVALID", ctx)
            return
        if args[2] in ['d', 'day', 'days']:
            time = 86400
        elif args[2] in ['h', 'hour', 'hours']:
            time = 3600
        elif args[2] in ['m', 'min', 'mins', 'minute', 'minutes']:
            time = 60
        else:
            await send("RM_TIMEOUT_INVALID", ctx)
            return
        try:
            time *= int(args[1])
            if time == 0:
                raise ValueError
        except ValueError:
            await send("RM_TIMEOUT_INVALID", ctx)
            return
        endTime = int(dt.timestamp(dt.now()))+time
        player.timeout = endTime
        await roleUpdate(player)
        await player.dbUpdate("timeout")
        await permsMuted(True, player.id)
        await send("RM_TIMEOUT", ctx, player.mention, dt.utcfromtimestamp(endTime).strftime("%Y-%m-%d %H:%M UTC"))

    @commands.command()
    @commands.guild_only()
    async def pog(self, ctx, *args):
        if len(args) == 0:
            await send("BOT_VERSION", ctx, cfg.VERSION, isAllLocked())
            return
        arg = args[0]
        if arg == "version":
            await send("BOT_VERSION", ctx, cfg.VERSION, isAllLocked())
            return
        if arg == "lock":
            if isAllLocked():
                await send("BOT_ALREADY", ctx, "locked")
                return
            lockAll(self.client)
            await send("BOT_LOCKED", ctx)
            return
        if arg == "unlock":
            if not isAllLocked():
                await send("BOT_ALREADY", ctx, "unlocked")
                return
            unlockAll(self.client)
            await send("BOT_UNLOCKED", ctx)
            return
        if arg == "ingame":
            if getOfflinePlayers.bypass:
                getOfflinePlayers.bypass = False
                await send("BOT_BP_OFF", ctx)
            else:
                getOfflinePlayers.bypass = True
                await send("BOT_BP_ON", ctx)
            return
        await send("WRONG_USAGE", ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def channel(self, ctx, *args):
        if ctx.channel.id not in [cfg.channels["register"], cfg.channels["lobby"], *cfg.channels["matches"]]:
            await send("WRONG_CHANNEL_2", ctx, ctx.command.name, f"<#{ctx.channel.id}>")
            return
        if len(args) == 1:
            arg = args[0]
            if arg == "freeze":
                await channelFreeze(True, ctx.channel.id)
                await send("BOT_FROZEN", ctx)
                return
            if arg == "unfreeze":
                await channelFreeze(False, ctx.channel.id)
                await send("BOT_UNFROZEN", ctx)
                return
        await send("WRONG_USAGE", ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def sub(self, ctx, *args):
        # Check for match status first maybe?
        player = await _removeChecks(ctx, cfg.channels["matches"])
        if player is None:
            return
        if player.status not in (PlayerStatus.IS_MATCHED, PlayerStatus.IS_PICKED):
            await send("SUB_NO", ctx)
            return
        if player.status is PlayerStatus.IS_PICKED and isinstance(player.active, TeamCaptain):
            await send("SUB_NO_CAPTAIN", ctx)
            return
        newPlayer = player.match.onPlayerSub(player)
        if newPlayer is None:
            await send("SUB_NO_PLAYER", ctx)
            return
        else:
            await channelSend("SUB_LOBBY",  cfg.channels["lobby"], newPlayer.mention, newPlayer.match.id,
                                            namesInLobby=getAllNamesInLobby())
            if newPlayer.status is PlayerStatus.IS_PICKED:
                await send("SUB_OKAY_TEAM", ctx, newPlayer.mention, player.mention,
                                            newPlayer.active.team.name, match=newPlayer.match)
            else:
                await send("SUB_OKAY", ctx, newPlayer.mention, player.mention, match=newPlayer.match)
            return



def setup(client):
    client.add_cog(AdminCog(client))


async def _removeChecks(ctx, channels):
    if not isinstance(channels, list):
        channels = [channels]
    if ctx.channel.id not in channels:
        await send("WRONG_CHANNEL", ctx, ctx.command.name, ", ".join(f"<#{cId}>" for cId in channels))
        return
    if len(ctx.message.mentions) != 1:
        await send("RM_MENTION_ONE", ctx)
        return
    try:
        player = getPlayer(ctx.message.mentions[0].id)
    except ElementNotFound:
        # player isn't even registered in the system...
        await send("RM_NOT_IN_DB", ctx)
        return
    return player
