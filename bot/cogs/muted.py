# @CHECK 2.0 features OK

# discord.py
from discord.ext import commands
from logging import getLogger
from datetime import datetime as dt

# Custom classes
from classes import Player

# Custom modules
import modules.config as cfg
from modules.roles import perms_muted, remove_roles, role_update
from display.strings import AllStrings as display

log = getLogger("pog_bot")


class MutedCog(commands.Cog, name='muted'):
    """
    Muted cog, handle the commands from register channel
    """

    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):  # Check if right channel
        return ctx.channel.id == cfg.channels['muted']

    @commands.command()
    @commands.guild_only()
    async def escape(self, ctx):
        player = Player.get(ctx.author.id)
        if not player:
            await perms_muted(False, ctx.author.id)
            await remove_roles(ctx.author.id)
            return
        if player.is_timeout:
            await display.MUTE_SHOW.send(ctx, dt.utcfromtimestamp(player.timeout).strftime("%Y-%m-%d %H:%M UTC"))
            return
        await role_update(player)
        await display.MUTE_FREED.send(ctx)
        await perms_muted(False, player.id)


def setup(client):
    client.add_cog(MutedCog(client))
