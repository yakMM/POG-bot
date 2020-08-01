from discord.ext import commands

import modules.config as cfg
from modules.enumerations import SelStatus, MatchStatus
from modules.display import send
from modules.exceptions import ElementNotFound
from modules.tools import isAdmin

from classes.maps import MapSelection, getMapSelection
from matches import clearLobby, getMatch, getAllNamesInLobby



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
            if match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
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
        try:
            sel = getMapSelection(id)
        except ElementNotFound:
            if len(args) == 0:
                await send("MAP_HELP", ctx)
                return
            sel = MapSelection(id)
        await sel.doSelectionProcess(ctx, *args) # Handle the actual map selection
        if sel.status == SelStatus.IS_SELECTED:
            sel.confirm()
            match.map = sel.map
            await send("MATCH_MAP_SELECTED", ctx, sel.map.name)


def setup(client):
    client.add_cog(AdminCog(client))
