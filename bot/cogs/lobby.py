# @CHECK 2.0 features OK

from discord.ext import commands
from discord import Status as discord_status
from logging import getLogger

from display.strings import AllStrings as display
from display.classes import ContextWrapper
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
            await display.UNKNOWN_ERROR.send(ctx, "Lobby Overflow")
            return
        try:
            player = get_player(ctx.message.author.id)
        except ElementNotFound:
            await display.EXT_NOT_REGISTERED.send(ctx,  cfg.channels["register"])
            return
        if player.status is PlayerStatus.IS_NOT_REGISTERED:
            await display.EXT_NOT_REGISTERED.send(ctx, cfg.channels["register"])
            return
        accs = player.accounts_flipped
        if len(accs) != 0:
            await display.CHECK_ACCOUNT.send(ctx, cfg.channels["register"], account_names=accs)
            return
        if ctx.author.status == discord_status.offline:
            await display.LB_OFFLINE.send(ctx)
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            await display.LB_ALREADY_IN.send(ctx)
            return
        if player.status is not PlayerStatus.IS_REGISTERED:
            await display.LB_IN_MATCH.send(ctx)
            return
        if is_lobby_stuck():
            await display.LB_STUCK_JOIN.send(ctx)
            return

        add_to_lobby(player)
        await display.LB_ADDED.send(ctx, names_in_lobby=get_all_names_in_lobby())

    @commands.command(aliases=['l'])
    @commands.guild_only()
    async def leave(self, ctx):
        """ Leave queue
        """
        try:
            player = get_player(ctx.message.author.id)
        except ElementNotFound:
            await display.LB_NOT_IN.send(ctx)
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            remove_from_lobby(player)
            await display.LB_REMOVED.send(ctx, names_in_lobby=get_all_names_in_lobby())
            return
        await display.LB_NOT_IN.send(ctx)

    @commands.command(aliases=['q'])
    @commands.guild_only()
    async def queue(self, ctx):
        """ Display queue
        """
        if get_lobby_len() > cfg.general["lobby_size"]:
            await display.UNKNOWN_ERROR.send(ctx, "Lobby Overflow")
            return
        if is_lobby_stuck():
            await display.LB_QUEUE.send(ctx, names_in_lobby=get_all_names_in_lobby())
            await display.LB_STUCK.send(ctx)
            return
        await display.LB_QUEUE.send(ctx, names_in_lobby=get_all_names_in_lobby())


def setup(client):
    client.add_cog(LobbyCog(client))
