from discord.ext import commands

import modules.config as cfg
from modules.enumerations import SelStatus, MatchStatus, PlayerStatus
from modules.display import send, channelSend
from modules.exceptions import ElementNotFound, DatabaseError
from modules.tools import isAdmin
from modules.database import remove
from modules.loader import lockAll, unlockAll, isAllLocked

from classes.players import removePlayer, getPlayer

from matches import clearLobby, getMatch, getAllNamesInLobby, removeFromLobby



class AdminCog(commands.Cog, name='admin'):
    """
    Register cog, handle the admin commands
    """

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('Admin Cog is online')

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
        if ctx.channel.id == cfg.discord_ids["lobby"]: # clear lobby
            if clearLobby():
                await send("LB_CLEARED", ctx, namesInLobby=getAllNamesInLobby())
                return
            await send("LB_EMPTY", ctx)
            return
        if ctx.channel.id in cfg.discord_ids["matches"]: # clear a match channel
            match = getMatch(ctx.channel.id)
            if match.status in (MatchStatus.IS_FREE, MatchStatus.IS_RUNNING):
                await send("MATCH_NO_MATCH", ctx, ctx.command.name)
                return
            if match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_RESULT):
                await send("MATCH_ALREADY_STARTED", ctx, ctx.command.name)
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
        if match.status in (MatchStatus.IS_FREE, MatchStatus.IS_RUNNING):
            await send("MATCH_NO_MATCH", ctx, ctx.command.name)
            return
        if match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
            await send("MATCH_ALREADY_STARTED", ctx, ctx.command.name)
            return
        sel = match.mapSelector
        await sel.doSelectionProcess(ctx, args) # Handle the actual map selection
        if sel.status == SelStatus.IS_SELECTED:
            match.confirmMap()
            await send("MATCH_MAP_SELECTED", ctx, sel.map.name)

    @commands.command()
    @commands.guild_only()
    async def unregister(self, ctx):
        if ctx.channel.id != cfg.discord_ids["register"]:
            await send("WRONG_CHANNEL", ctx, ctx.command.name, f"<#{cfg.discord_ids['register']}>")
            return
        if len(ctx.message.mentions) != 1:
            await send("RM_MENTION_ONE", ctx)
            return
        try:
            player = getPlayer(ctx.message.mentions[0].id)
        except ElementNotFound:
            await send("RM_NOT_IN_DB", ctx) # player isn't even registered in the system...
            return
        if player.status == PlayerStatus.IS_LOBBIED:
            removeFromLobby(player)
            await channelSend("RM_LOBBY", cfg.discord_ids["lobby"], player.mention, namesInLobby=getAllNamesInLobby())
        if player.status in (PlayerStatus.IS_REGISTERED, PlayerStatus.IS_NOT_REGISTERED):
            try:
                await remove(player)
            except DatabaseError:
                pass # ignored if not yet in db
            memb = ctx.author.guild.get_member(player.id)
            removePlayer(player)
            notify = memb.guild.get_role(cfg.discord_ids["notify_role"])
            registered = memb.guild.get_role(cfg.discord_ids["registered_role"])
            await memb.remove_roles(notify)
            await memb.remove_roles(registered)
            await send("RM_OK", ctx)
            return
        await send("RM_IN_MATCH", ctx)

    @commands.command()
    @commands.guild_only()
    async def pog(self, ctx, *args):
        if len(args) == 0:
            await send("BOT_VERSION", ctx, cfg.VERSION, isAllLocked())
            return
        arg = args[0]
        if arg=="version":
            await send("BOT_VERSION", ctx, cfg.VERSION, isAllLocked())
            return
        if arg=="lock":
            if isAllLocked():
                await send("BOT_ALREADY", ctx, "locked")
                return
            lockAll(self.client)
            await send("BOT_LOCKED", ctx)
            return
        if arg=="unlock":
            if not isAllLocked():
                await send("BOT_ALREADY", ctx, "unlocked")
                return
            unlockAll(self.client)
            await send("BOT_UNLOCKED", ctx)
            return
        await send("WRONG_USAGE", ctx, ctx.command.name)
        return


def setup(client):
    client.add_cog(AdminCog(client))
