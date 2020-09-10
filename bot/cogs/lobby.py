from discord.ext import commands
from discord import Status as discordStatus
from logging import getLogger

from modules.display import send, channelSend
import modules.config as cfg
from modules.exceptions import UnexpectedError, ElementNotFound, LobbyStuck

from classes.players import PlayerStatus, getPlayer

from matches import getLobbyLen, isLobbyStuck, removeFromLobby, addToLobby, getAllNamesInLobby

log = getLogger(__name__)


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
        if getLobbyLen() > cfg.general["lobby_size"]:  # This should not happen EVER
            await send("UNKNOWN_ERROR", ctx, "Lobby Overflow")
            return
        try:
            player = getPlayer(ctx.message.author.id)
        except ElementNotFound:
            await send("EXT_NOT_REGISTERED", ctx,  cfg.channels["register"])
            return
        if player.status is PlayerStatus.IS_NOT_REGISTERED:
            await send("EXT_NOT_REGISTERED", ctx, cfg.channels["register"])
            return
        if ctx.author.status == discordStatus.offline:
            await send("LB_OFFLINE", ctx)
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            await send("LB_ALREADY_IN", ctx)
            return
        if player.status is not PlayerStatus.IS_REGISTERED:
            await send("LB_IN_MATCH", ctx)
            return
        if isLobbyStuck():
            await send("LB_STUCK_JOIN", ctx)
            return

        addToLobby(player)
        await send("LB_ADDED", ctx, namesInLobby=getAllNamesInLobby())

    @commands.command(aliases=['l'])
    @commands.guild_only()
    async def leave(self, ctx):
        """ Leave queue
        """
        try:
            player = getPlayer(ctx.message.author.id)
        except ElementNotFound:
            await send("LB_NOT_IN", ctx)
            return
        if player.status is PlayerStatus.IS_LOBBIED:
            removeFromLobby(player)
            await send("LB_REMOVED", ctx, namesInLobby=getAllNamesInLobby())
            return
        await send("LB_NOT_IN", ctx)

    @commands.command(aliases=['q'])
    @commands.guild_only()
    async def queue(self, ctx):
        """ Display queue
        """
        if getLobbyLen() > cfg.general["lobby_size"]:
            await send("UNKNOWN_ERROR", ctx, "Lobby Overflow")
            return
        if isLobbyStuck():
            await send("LB_QUEUE", ctx, namesInLobby=getAllNamesInLobby())
            await send("LB_STUCK", ctx)
            return
        await send("LB_QUEUE", ctx, namesInLobby=getAllNamesInLobby())


def setup(client):
    client.add_cog(LobbyCog(client))
