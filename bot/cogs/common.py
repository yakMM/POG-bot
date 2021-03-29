from discord.ext import commands
from logging import getLogger

import modules.config as cfg
import modules.lobby as lobby

from match_process.match import Match
from display import AllStrings as disp
from match_process import MatchStatus

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
            if match.status is MatchStatus.IS_FREE:
                await disp.MATCH_NO_MATCH.send(ctx, ctx.command.name)
            else:
                try:
                    await match.info()
                except AttributeError:
                    await disp.PK_SHOW_TEAMS.send(ctx, match=match)
            return
        await disp.WRONG_CHANNEL_2.send(ctx, ctx.command.name, f"<#{ctx.channel.id}>")


def setup(client):
    client.add_cog(MatchesCog(client))
