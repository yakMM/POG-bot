# @CHECK 2.0 features OK

# discord.py
from discord.ext import commands
from logging import getLogger
from datetime import datetime as dt

# Custom modules
import modules.config as cfg
import modules.database as db
import modules.tools as tools
import modules.stat_processor as stat_processor

from classes import PlayerStat, Player

from display import AllStrings as disp, ContextWrapper

log = getLogger("pog_bot")


class RegisterCog(commands.Cog, name='usage'):
    """
    Muted cog, handle the commands from register channel
    """

    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):  # Check if right channel
        return ctx.channel.id == cfg.channels['usage']

    @commands.command(aliases=['u'])
    @commands.guild_only()
    async def usage(self, ctx, *args):
        if len(ctx.message.mentions) == 1:
            r_id = ctx.message.mentions[0].id
        else:
            try:
                r_id = int(args[0])
            except (ValueError, IndexError):
                await disp.RM_MENTION_ONE.send(ctx)
                return
        data = await db.async_db_call(db.get_element, "accounts_usage", r_id)
        if not data or (data and len(data["usages"]) == 0):
            await disp.NO_DATA.send(ctx)
        else:
            await disp.ACCOUNT_USAGE.send(ctx, data=data)

    @commands.command()
    @commands.guild_only()
    async def stats(self, ctx, *args):
        if len(ctx.message.mentions) == 1:
            p_id = ctx.message.mentions[0].id
        else:
            await disp.RM_MENTION_ONE.send(ctx)
            return

        stat_player = await PlayerStat.get_from_database(p_id, "N/A")
        if stat_player.nb_matches_played == 0:
            await disp.NO_DATA.send(ctx)
            return

        time = 0
        if len(args) > 0:
            time = tools.time_calculator(" ".join(args))
            if time == 0:
                await disp.WRONG_USAGE.send(ctx, ctx.command.name)
                return
            time = tools.timestamp_now() - tools.time_calculator(" ".join(args))
        else:
            time = stat_processor.oldest

        num = len(stat_processor.get_matches_in_time(stat_player, time))
        t_str = tools.time_diff(time)
        num_str = ""
        suffix = ""
        if num == 0:
            num_str = "no"
        else:
            num_str = str(num)
        if num > 1:
            suffix = "es"

        await disp.DISPLAY_USAGE.send(ctx, p_id, num_str, suffix, t_str, dt.utcfromtimestamp(time).strftime("%Y-%m-%d %H:%M UTC"))

    @commands.command()
    @commands.guild_only()
    async def psb(self, ctx, *args):
        if len(ctx.message.mentions) == 1:
            p_id = ctx.message.mentions[0].id
        else:
            await disp.RM_MENTION_ONE.send(ctx)
            return

        player = Player.get(p_id)
        if player:
            name = player.name
        else:
            name = "Unknown"
        stat_player = await PlayerStat.get_from_database(p_id, name)
        if stat_player.nb_matches_played == 0:
            await disp.NO_DATA.send(ctx)
            return

        req_date, usages = stat_processor.format_for_psb(stat_player, args)

        await disp.PSB_USAGE.send(ctx, stat_player.mention, req_date, player=stat_player, usages=usages)


def setup(client):
    client.add_cog(RegisterCog(client))
