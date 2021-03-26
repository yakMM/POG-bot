# @CHECK 2.0 features OK

# discord.py
from discord.ext import commands
from logging import getLogger

# Custom modules
import modules.config as cfg
import modules.database as db

from display import AllStrings as disp, ContextWrapper

log = getLogger("pog_bot")


class RegisterCog(commands.Cog, name='muted'):
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
        if len(args) != 1:
            await disp.WRONG_USAGE.send(ctx, ctx.command.name)
            return
        arg = args[0]
        if len(ctx.message.mentions) == 1:
            r_id = ctx.message.mentions[0].id
        else:
            try:
                r_id = int(arg)
            except ValueError:
                await disp.WRONG_USAGE.send(ctx, ctx.command.name)
                return
        data = await db.async_db_call(db.get_element, "accounts_usage", r_id)
        if not data:
            await disp.USAGE_NOT_FOUND.send(ctx)
        elif len(data["usages"]) == 0:
            await disp.USAGE_NO.send(ctx)
        else:
            await disp.ACCOUNT_USAGE.send(ctx, data=data)



def setup(client):
    client.add_cog(RegisterCog(client))
