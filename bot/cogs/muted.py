# @CHECK 2.0 features OK

# discord.py
from discord.ext import commands
from logging import getLogger
from datetime import datetime as dt

# Custom classes
from classes.players import get_player

# Custom modules
import modules.config as cfg
from modules.roles import perms_muted, force_info, role_update
from modules.exceptions import ElementNotFound
from display import send
from modules.exceptions import ElementNotFound

log = getLogger(__name__)


class RegisterCog(commands.Cog, name='muted'):
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
        try:
            player = get_player(ctx.author.id)
        except ElementNotFound:
            await perms_muted(False, ctx.author.id)
            await force_info(ctx.author.id)
            return
        if player.is_timeout:
            await send("MUTE_SHOW", ctx, dt.utcfromtimestamp(player.timeout).strftime("%Y-%m-%d %H:%M UTC"))
            return
        await role_update(player)
        await send("MUTE_FREED", ctx)
        await perms_muted(False, player.id)


def setup(client):
    client.add_cog(RegisterCog(client))
