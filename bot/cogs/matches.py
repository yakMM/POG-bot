from discord.ext import commands
import modules.config as cfg
from match.classes import Match


class MatchesCog(commands.Cog, name='matches'):
    """
    Matches cog, handle the user commands in matches channels
    """

    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):
        # Check if right channel
        return ctx.channel.id in cfg.channels['matches']

    """
    commands:

    =captain
    =sub
    =pick
    =base
    =ready
    =squittal
    """

    @commands.command(aliases=['c', 'cap'])
    @commands.guild_only()
    async def captain(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        await match.command.captain(ctx, args)

    @commands.command()
    @commands.guild_only()
    async def sub(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        await match.command.sub(ctx, args)

    @commands.command(aliases=['p'])
    @commands.guild_only()
    async def pick(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        await match.command.pick(ctx, args)

    @commands.command(aliases=['b', 'map'])
    @commands.guild_only()
    async def base(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        await match.command.base(ctx, args)

    @commands.command(aliases=['rdy'])
    @commands.guild_only()
    async def ready(self, ctx):  # when ready
        match = Match.get(ctx.channel.id)
        await match.command.ready(ctx)

    @commands.command()
    @commands.guild_only()
    async def squittal(self, ctx):
        match = Match.get(ctx.channel.id)
        await match.command.squittal(ctx)


def setup(client):
    client.add_cog(MatchesCog(client))

