from discord.ext import commands
import modules.config as cfg
from match.classes import Match
from classes import Base


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

    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(number=1, wait=True)
    async def sub(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        await match.command.sub(ctx, args)

    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(number=1, wait=True)
    async def swap(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        await match.command.swap(ctx, args)

    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(number=1, wait=True)
    async def bench(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        await match.command.bench(ctx, args, bench=True)

    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(number=1, wait=True)
    async def unbench(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        await match.command.bench(ctx, args, bench=False)

    @commands.command(aliases=['p'])
    @commands.guild_only()
    @commands.max_concurrency(number=1, wait=True)
    async def pick(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        arg = " ".join(args)

        # To allow changing base with =p:
        if arg not in ("vs", "tr", "nc", "help", "h"):  # Those args are reserved for =p
            # bl is True if arg is detected to relate to base picking
            bl = arg in ("list", "l")
            bl = bl or Base.get_bases_from_name(arg, base_pool=True)
            if bl:
                await match.command.base(ctx, args)
                return
        await match.command.pick(ctx, args)

    @commands.command(aliases=['b', 'map'])
    @commands.guild_only()
    @commands.max_concurrency(number=1, wait=True)
    async def base(self, ctx, *args):
        match = Match.get(ctx.channel.id)
        await match.command.base(ctx, args)

    @commands.command(aliases=['rdy'])
    @commands.guild_only()
    @commands.max_concurrency(number=1, wait=True)
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

