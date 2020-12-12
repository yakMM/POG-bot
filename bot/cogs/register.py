# @CHECK 2.0 features OK

# discord.py
from discord.ext import commands
from logging import getLogger

# Custom classes
from classes.players import Player, get_player

# Custom modules
import modules.config as cfg
from modules.enumerations import PlayerStatus
from display import send
from modules.tools import is_al_num
from modules.exceptions import UnexpectedError, ElementNotFound, CharNotFound, CharInvalidWorld, CharMissingFaction, CharAlreadyExists, ApiNotReachable

log = getLogger("pog_bot")


class RegisterCog(commands.Cog, name='register'):
    """
    Register cog, handle the commands from register channel
    """

    def __init__(self, client):
        self.client = client

    """
    Registered Commands:

    =register
    """

    async def cog_check(self, ctx):  # Check if right channel
        return ctx.channel.id == cfg.channels['register']

    @commands.command(aliases=['r'])
    @commands.guild_only()
    async def register(self, ctx, *args):
        if len(ctx.message.mentions) != 0:  # Don't want a mention here
            await send("REG_INVALID", ctx)
            return
        try:
            player = get_player(ctx.author.id)
        except ElementNotFound:
            await send("REG_NO_RULE", ctx, cfg.channels["rules"])
            return

        msg = await _register(player, ctx, args)

    @commands.command()
    @commands.guild_only()
    async def notify(self, ctx):
        try:
            player = get_player(ctx.author.id)
        except ElementNotFound:
            await send("REG_NO_RULE", ctx, cfg.channels["rules"])
            return
        if player.is_notify:
            player.is_notify = False
            await send("NOTIFY_REMOVED", ctx)
        else:
            player.is_notify = True
            await send("NOTIFY_ADDED", ctx)
        await player.db_update("notify")


def setup(client):
    client.add_cog(RegisterCog(client))


async def _register(player, ctx, args):
    """
    Set player's ingame name(s).

    Check if inputted names are valid ingame names and find the id for each name.
    Check the faction of each name and registered the name for the player

    Parameters:
    ingame_names (str, list of str): If a list, will add each name one by one.
    If a string, will add the faction suffixes automatically.
    """
    if player.status is PlayerStatus.IS_PLAYING:  # Can't register if already playing
        await send("REG_FROZEN", ctx)
        return
    for name in args:
        if not is_al_num(name):  # Char names are only alphanum names
            await send("INVALID_STR", ctx, name)
            return
    if len(args) == 0:  # If user did not input any arg, display their current registration status
        if player.status is PlayerStatus.IS_NOT_REGISTERED:
            await send("REG_NOT_REGISTERED", ctx)
            return
        if player.has_own_account:
            await send("REG_IS_REGISTERED_OWN", ctx, *player.ig_names)
            return
        await send("REG_IS_REGISTERED_NOA", ctx)
        return
    # store previous status
    was_player_registered = player.status is not PlayerStatus.IS_NOT_REGISTERED
    if len(args) == 1 or len(args) == 3:  # if 1 or 3 args
        if len(args) == 1 and args[0] == "help":  # =r help displays hel^p
            await send("REG_HELP", ctx)
            return
        try:
            # player.register return a boolean: has_the_profile_been_updated
            if not await player.register(args):
                # if no update, say "you are already registered etc"
                await send("REG_IS_REGISTERED_OWN", ctx, *player.ig_names)
                return
            if was_player_registered:
                await send("REG_UPDATE_OWN", ctx, *player.ig_names)
                return
            await send("REG_WITH_CHARS", ctx, *player.ig_names)
            return
        except CharNotFound as e:  # if problems with chars
            await send("REG_CHAR_NOT_FOUND", ctx, e.char)
            return
        except CharInvalidWorld as e:
            await send("REG_NOT_JAEGER", ctx, e.char)
            return
        except CharMissingFaction as e:
            await send("REG_MISSING_FACTION", ctx, e.faction)
            return
        except CharAlreadyExists as e:
            await send("REG_ALREADY_EXIST", ctx, e.char, e.player.mention)
            return
        except ApiNotReachable:
            await send("API_ERROR", ctx)
            return
        except UnexpectedError as e:
            await send("UNKNOWN_ERROR", ctx, e.reason)
            return
    if len(args) == 2:  # if 2 args, it should be "no account", if not, invalid request. Again, check if update and push db if that's the case
        if args[0] == "no" and args[1] == "account":
            if player.status is PlayerStatus.IS_WAITING:  # Can't register if already playing
                await send("REG_FROZEN_2", ctx)
                return
            if not await player.register(None):
                await send("REG_IS_REGISTERED_NOA", ctx)
                return
            if was_player_registered:
                await send("REG_UPDATE_NOA", ctx)
                return
            await send("REG_NO_ACCOUNT", ctx)
            return
    await send("REG_INVALID", ctx)  # if any other number of args, not valid
    return
