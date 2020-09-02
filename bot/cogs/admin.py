from discord.ext import commands
from logging import getLogger

import modules.config as cfg
from modules.enumerations import SelStatus, MatchStatus, PlayerStatus
from modules.display import send, channelSend
from modules.exceptions import ElementNotFound, DatabaseError
from modules.tools import isAdmin
from modules.database import removePlayer as dbRemove
from modules.loader import lockAll, unlockAll, isAllLocked
from modules.roles import getRole, forceInfo

from classes.players import removePlayer, getPlayer

from matches import clearLobby, getMatch, getAllNamesInLobby, removeFromLobby


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
        if ctx.channel.id == cfg.discord_ids["lobby"]:  # clear lobby
            if clearLobby():
                await send("LB_CLEARED", ctx, namesInLobby=getAllNamesInLobby())
                return
            await send("LB_EMPTY", ctx)
            return
        # clear a match channel
        if ctx.channel.id in cfg.discord_ids["matches"]:
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
        if channelId not in cfg.discord_ids["matches"]:
            await send("WRONG_CHANNEL", ctx, ctx.command.name, " channels " + ", ".join(f'<#{id}>' for id in cfg.discord_ids["matches"]))
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
        player = await _removeChecks(ctx, "register")
        if player is None:
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            removeFromLobby(player)
            await channelSend("RM_LOBBY", cfg.discord_ids["lobby"], player.mention, namesInLobby=getAllNamesInLobby())
        if player.status in (PlayerStatus.IS_REGISTERED, PlayerStatus.IS_NOT_REGISTERED):
            try:
                await dbRemove(player)
            except DatabaseError:
                pass  # ignored if not yet in db
            removePlayer(player)
            forceInfo(player)
            await send("RM_OK", ctx)
            return
        await send("RM_IN_MATCH", ctx)
    
    @commands.command()
    @commands.guild_only()
    async def remove(self, ctx):
        player = await _removeChecks(ctx, "lobby")
        if player is None:
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            removeFromLobby(player)
            await channelSend("RM_LOBBY", cfg.discord_ids["lobby"], player.mention, namesInLobby=getAllNamesInLobby())
        await send("RM_NOT_LOBBIED", ctx)

    # WIP
    # @commands.command()
    # @commands.guild_only()
    # async def timeout(self, ctx, *args):
    #     if len(ctx.message.mentions) != 1:
    #         await send("RM_MENTION_ONE", ctx)
    #         return
    #     try:
    #         player = getPlayer(ctx.message.mentions[0].id)
    #     except ElementNotFound:
    #         # player isn't even registered in the system...
    #         await send("RM_NOT_IN_DB", ctx)
    #         return
    #     if player.status is PlayerStatus.IS_LOBBIED:
    #         removeFromLobby(player)
    #         await channelSend("RM_LOBBY", cfg.discord_ids["lobby"], player.mention, namesInLobby=getAllNamesInLobby())
    #     if player.status not in (PlayerStatus.IS_REGISTERED, PlayerStatus.IS_NOT_REGISTERED):
    #         await send("RM_IN_MATCH", ctx)
    #         return
        
    #     player.addTimeout
    #     forceInfo(player)



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
        await send("WRONG_USAGE", ctx, ctx.command.name)

    @commands.command()
    @commands.guild_only()
    async def channel(self, ctx, *args):
        if len(args) == 1:
            arg = args[0]
            memb = ctx.author
            notify = memb.guild.get_role(cfg.discord_ids["notify_role"])
            registered = memb.guild.get_role(
                cfg.discord_ids["registered_role"])
            ov_notify = ctx.channel.overwrites_for(notify)
            ov_registered = ctx.channel.overwrites_for(registered)
            if arg == "freeze":
                ov_notify.send_messages = False
                ov_registered.send_messages = False
                await ctx.channel.set_permissions(notify, overwrite=ov_notify)
                await ctx.channel.set_permissions(registered, overwrite=ov_registered)
                await send("BOT_FROZEN", ctx)
                return
            if arg == "unfreeze":
                ov_notify.send_messages = True
                ov_registered.send_messages = True
                await ctx.channel.set_permissions(notify, overwrite=ov_notify)
                await ctx.channel.set_permissions(registered, overwrite=ov_registered)
                await send("BOT_UNFROZEN", ctx)
                return
        await send("WRONG_USAGE", ctx, ctx.command.name)


def setup(client):
    client.add_cog(AdminCog(client))

async def _removeChecks(ctx, channel):
    if ctx.channel.id != cfg.discord_ids[channel]:
        await send("WRONG_CHANNEL", ctx, ctx.command.name, f"<#{cfg.discord_ids[channel]}>")
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