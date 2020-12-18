# @CHECK 2.0 features OK

from discord.ext import commands
from discord import Status as discord_status
from logging import getLogger

from display import send
import modules.config as cfg
from modules.exceptions import UnexpectedError, ElementNotFound, LobbyStuck

from classes.players import PlayerStatus, get_player

from modules.lobby import get_lobby_len, is_lobby_stuck, remove_from_lobby, add_to_lobby, get_all_names_in_lobby

from match_process import Match

log = getLogger("pog_bot")


class LobbyCog(commands.Cog, name='lobby'):
    """
    Lobby cog, handle the commands from lobby channel
    """

    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):
        return ctx.channel.id == cfg.channels['lobby']

    """
    Commands:

    =join
    =leave
    =queue
    """

    @commands.command(aliases=['j'])
    @commands.guild_only()
    @commands.max_concurrency(number=1, wait=True)
    async def join(self, ctx):
        """ Join queue
        """
        if get_lobby_len() > cfg.general["lobby_size"]:  # This should not happen EVER
            await send("UNKNOWN_ERROR", ctx, "Lobby Overflow")
            return
        try:
            player = get_player(ctx.message.author.id)
        except ElementNotFound:
            await send("EXT_NOT_REGISTERED", ctx,  cfg.channels["register"])
            return
        if player.status is PlayerStatus.IS_NOT_REGISTERED:
            await send("EXT_NOT_REGISTERED", ctx, cfg.channels["register"])
            return
        accs = player.accounts_flipped
        if len(accs) != 0:
            await send("CHECK_ACCOUNT", ctx, cfg.channels["register"], account_names=accs)
            return
        if ctx.author.status == discord_status.offline:
            await send("LB_OFFLINE", ctx)
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            await send("LB_ALREADY_IN", ctx)
            return
        if player.status is not PlayerStatus.IS_REGISTERED:
            await send("LB_IN_MATCH", ctx)
            return
        if is_lobby_stuck():
            await send("LB_STUCK_JOIN", ctx)
            return

        add_to_lobby(player)
        await send("LB_ADDED", ctx, names_in_lobby=get_all_names_in_lobby())

    @commands.command(aliases=['l'])
    @commands.guild_only()
    async def leave(self, ctx):
        """ Leave queue
        """
        try:
            player = get_player(ctx.message.author.id)
        except ElementNotFound:
            await send("LB_NOT_IN", ctx)
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            remove_from_lobby(player)
            await send("LB_REMOVED", ctx, names_in_lobby=get_all_names_in_lobby())
            return
        await send("LB_NOT_IN", ctx)

    @commands.command(aliases=['q'])
    @commands.guild_only()
    async def queue(self, ctx):
        """ Display queue
        """
        if get_lobby_len() > cfg.general["lobby_size"]:
            await send("UNKNOWN_ERROR", ctx, "Lobby Overflow")
            return
        if is_lobby_stuck():
            await send("LB_QUEUE", ctx, names_in_lobby=get_all_names_in_lobby())
            await send("LB_STUCK", ctx)
            return
        await send("LB_QUEUE", ctx, names_in_lobby=get_all_names_in_lobby())


def setup(client):
    client.add_cog(LobbyCog(client))
