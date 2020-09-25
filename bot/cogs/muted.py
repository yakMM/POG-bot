# @CHECK 2.0 features OK

# discord.py
from discord.ext import commands
from logging import getLogger
from datetime import datetime as dt

# Custom classes
from classes.players import getPlayer

# Custom modules
import modules.config as cfg
from modules.roles import permsMuted, forceInfo, roleUpdate
from modules.exceptions import ElementNotFound
from modules.display import send
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
            player = getPlayer(ctx.author.id)
        except ElementNotFound:
            await permsMuted(False, ctx.author.id)
            await forceInfo(ctx.author.id)
            return
        if player.isTimeout:
            await send("MUTE_SHOW", ctx, dt.utcfromtimestamp(player.timeout).strftime("%Y-%m-%d %H:%M UTC"))
            return
        await roleUpdate(player)
        await send("MUTE_FREED", ctx)
        await permsMuted(False, player.id)


def setup(client):
    client.add_cog(RegisterCog(client))
