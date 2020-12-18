# @CHECK 2.0 features OK

from discord.ext import commands
from logging import getLogger

import modules.config as cfg
from modules.lobby import get_all_names_in_lobby
from match_process import Match
from display import send
from modules.enumerations import MatchStatus

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
            await send("GLOBAL_INFO", ctx, lobby=get_all_names_in_lobby(), match_list=match_list)
            return

        if ctx.channel.id in cfg.channels["matches"]:
            match = Match.get(ctx.channel.id)
            if match.status not in (MatchStatus.IS_FREE, MatchStatus.IS_RUNNING):
                await send("PK_SHOW_TEAMS", ctx, match=match)
            else:
                await send("MATCH_NO_MATCH", ctx, ctx.command.name)
            return

        await send("WRONG_CHANNEL_2", ctx, ctx.command.name, f"<#{ctx.channel.id}>")
        

def setup(client):
    client.add_cog(MatchesCog(client))

