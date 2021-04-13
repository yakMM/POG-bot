# @CHECK 2.0 features OK

from discord.ext import commands
from discord import Status as discord_status
from logging import getLogger

from display import AllStrings as disp
import modules.config as cfg

from classes import Player


import modules.lobby as lobby

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
    commands:

    =join
    =leave
    =queue
    """

    @commands.command(aliases=['j'])
    @commands.guild_only()
    async def join(self, ctx):
        """ Join queue
        """
        if lobby.get_lobby_len() > cfg.general["lobby_size"]:  # This should not happen EVER
            await disp.UNKNOWN_ERROR.send(ctx, "Lobby Overflow")
            return
        player = Player.get(ctx.message.author.id)
        if not player:
            await disp.EXT_NOT_REGISTERED.send(ctx,  cfg.channels["register"])
            return
        if not player.is_registered:
            await disp.EXT_NOT_REGISTERED.send(ctx, cfg.channels["register"])
            return
        accs = player.accounts_flipped
        if len(accs) != 0:
            await disp.CHECK_ACCOUNT.send(ctx, cfg.channels["register"], account_names=accs)
            return
        if player.is_lobbied:
            await disp.LB_ALREADY_IN.send(ctx)
            return
        if player.match:
            await disp.LB_IN_MATCH.send(ctx)
            return
        if lobby.is_lobby_stuck():
            await disp.LB_STUCK_JOIN.send(ctx)
            return

        names = lobby.add_to_lobby(player)
        await disp.LB_ADDED.send(ctx, names_in_lobby=names)

    @commands.command(aliases=['rst'])
    @commands.guild_only()
    async def reset(self, ctx):
        """ Join queue
        """
        player = Player.get(ctx.message.author.id)
        if not player or (player and not player.is_lobbied):
            await disp.LB_NOT_IN.send(ctx)
            return
        lobby.reset_timeout(player)
        await disp.LB_REFRESHED.send(ctx)

    @commands.command(aliases=['l'])
    @commands.guild_only()
    async def leave(self, ctx):
        """ Leave queue
        """
        player = Player.get(ctx.message.author.id)
        if not player:
            await disp.LB_NOT_IN.send(ctx)
            return
        if player.is_lobbied:
            lobby.remove_from_lobby(player)
            await disp.LB_REMOVED.send(ctx, names_in_lobby=lobby.get_all_names_in_lobby())
            return
        await disp.LB_NOT_IN.send(ctx)

    @commands.command(aliases=['q'])
    @commands.guild_only()
    async def queue(self, ctx):
        """ disp queue
        """
        if lobby.get_lobby_len() > cfg.general["lobby_size"]:
            await disp.UNKNOWN_ERROR.send(ctx, "Lobby Overflow")
            return
        if lobby.is_lobby_stuck():
            await disp.LB_QUEUE.send(ctx, names_in_lobby=lobby.get_all_names_in_lobby())
            await disp.LB_STUCK.send(ctx)
            return
        await disp.LB_QUEUE.send(ctx, names_in_lobby=lobby.get_all_names_in_lobby())


def setup(client):
    client.add_cog(LobbyCog(client))
