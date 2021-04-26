from discord.ext import commands
from logging import getLogger

import modules.config as cfg
import modules.lobby as lobby
from cogs.admin import get_check_player

from match.classes.match import Match
from display import AllStrings as disp, ContextWrapper
from match import MatchStatus

log = getLogger("pog_bot")


class MatchesCog(commands.Cog, name='common'):
    """
    Register cog, handle the commands in matches channels
    """

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=['i'])
    @commands.guild_only()
    async def info(self, ctx):
        if ctx.channel.id == cfg.channels["lobby"]:
            match_list = list()
            for ch in cfg.channels["matches"]:
                match_list.append(Match.get(ch))
            await disp.GLOBAL_INFO.send(ctx, lobby=lobby.get_all_names_in_lobby(), match_list=match_list)
            return

        if ctx.channel.id in cfg.channels["matches"]:
            match = Match.get(ctx.channel.id)
            await match.command.info(ctx)
            return
        await disp.WRONG_CHANNEL_2.send(ctx, ctx.command.name, f"<#{ctx.channel.id}>")

    @commands.command(aliases=['rm'])
    @commands.guild_only()
    async def remove(self, ctx):
        if ctx.channel.id == cfg.channels["lobby"]:
            player = await get_check_player(ctx)
            if not player:
                return
            if player.is_lobbied:
                lobby.remove_from_lobby(player)
                await disp.RM_LOBBY.send(ContextWrapper.channel(cfg.channels["lobby"]), player.mention,
                                         names_in_lobby=lobby.get_all_names_in_lobby())
                return
            await disp.RM_NOT_LOBBIED.send(ctx)
            return
        # if ctx.channel.id == cfg.channels["register"]:
        #     player = await get_check_player(ctx)
        #     if not player:
        #         return
        #     #TODO: remove ig names
        if ctx.channel.id in cfg.channels["matches"]:
            match = Match.get(ctx.channel.id)
            await match.command.bench(ctx)
            return
        else:
            await disp.WRONG_CHANNEL_2.send(ctx, ctx.command.name, f"<#{ctx.channel.id}>")


def setup(client):
    client.add_cog(MatchesCog(client))
