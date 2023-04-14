# @CHECK 2.0 features OK

# discord.py
from discord.ext import commands
from logging import getLogger

# Custom classes
import classes

# Custom modules
import modules.config as cfg
import modules.lobby as lobby
from display.strings import AllStrings as display
from modules.tools import is_al_num
from modules.tools import UnexpectedError
from modules.asynchttp import ApiNotReachable
from modules.roles import role_update

log = getLogger("pog_bot")


class RegisterCog(commands.Cog, name='register'):
    """
    Register cog, handle the commands from register channel
    """

    def __init__(self, client):
        self.client = client

    """
    Registered commands:

    =register
    """

    async def cog_check(self, ctx):  # Check if right channel
        return ctx.channel.id == cfg.channels['register']

    @commands.command(aliases=['r'])
    @commands.guild_only()
    async def register(self, ctx, *args):
        if len(ctx.message.mentions) != 0:  # Don't want a mention here
            await display.REG_INVALID.send(ctx)
            return
        player = classes.Player.get(ctx.author.id)
        if not player:
            await display.NO_RULE.send(ctx, f"={ctx.command.name}", cfg.channels["rules"])
            return

        await _register(player, ctx, args)

    @commands.command()
    @commands.guild_only()
    async def notify(self, ctx):
        player = classes.Player.get(ctx.author.id)
        if not player:
            await display.NO_RULE.send(ctx, f"={ctx.command.name}", cfg.channels["rules"])
            return
        if player.is_notify:
            player.is_notify = False
            await display.NOTIFY_REMOVED.send(ctx)
        else:
            player.is_notify = True
            await display.NOTIFY_ADDED.send(ctx)
        await role_update(player)
        await player.db_update("notify")

    @commands.command()
    @commands.guild_only()
    async def dm(self, ctx):
        player = classes.Player.get(ctx.author.id)
        if not player:
            await display.NO_RULE.send(ctx, f"={ctx.command.name}", cfg.channels["rules"])
            return
        if player.is_dm:
            player.is_dm = False
            await display.DM_REMOVED.send(ctx)
        else:
            player.is_dm = True
            await display.DM_ADDED.send(ctx)
        await player.db_update("dm")

    @commands.command()
    @commands.guild_only()
    async def quit(self, ctx):
        player = classes.Player.get(ctx.author.id)
        if not player:
            await display.NO_RULE.send(ctx, f"={ctx.command.name}", cfg.channels["rules"])
            return
        if player.active:
            await display.AWAY_BLOCKED.send(ctx)
            return
        if player.is_lobbied:
            lobby.remove_from_lobby(player)
        player.is_away = True
        await display.AWAY_GONE.send(ctx, player.mention)
        await role_update(player)
        await player.db_update("away")


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
    if player.active and player.active.is_playing:  # Can't register if already playing
        await display.REG_FROZEN.send(ctx)
        return
    for name in args:
        if not is_al_num(name):  # Char names are only alphanum names
            await display.INVALID_STR.send(ctx, name)
            return
    if len(args) == 0:  # If user did not input any arg, display. their current registration status
        if not player.is_registered:
            await display.REG_NOT_REGISTERED.send(ctx)
            return
        await display.REG_STATUS.send(ctx, player=player)
        return
    # store previous status
    was_player_registered = player.is_registered
    if len(args) == 1 or len(args) == 3:  # if 1 or 3 args
        if len(args) == 1 and args[0] == "help":  # =r help display the help
            await display.REG_HELP.send(ctx)
            return
        try:
            # player.register return a boolean: has_the_profile_been_updated
            if not await player.register(args):
                # if no update, say "you are already registered etc"
                await display.REG_ALREADY_OWN.send(ctx, *player.ig_names)
                return
            if was_player_registered:
                await display.REG_UPDATE_OWN.send(ctx, *player.ig_names)
                return
            await display.REG_WITH_CHARS.send(ctx, *player.ig_names)
            return
        except classes.CharNotFound as e:  # if problems with chars
            await display.REG_CHAR_NOT_FOUND.send(ctx, e.char)
            return
        except classes.CharInvalidWorld as e:
            await display.REG_NOT_JAEGER.send(ctx, e.char)
            return
        except classes.CharMissingFaction as e:
            await display.REG_MISSING_FACTION.send(ctx, e.faction)
            return
        except classes.CharAlreadyExists as e:
            await display.REG_ALREADY_EXIST.send(ctx, e.char, e.player.mention)
            return
        except ApiNotReachable:
            await display.API_ERROR.send(ctx)
            return
        except UnexpectedError as e:
            await display.UNKNOWN_ERROR.send(ctx, e.reason)
            return
    if len(args) == 2:  # if 2 args, it should be "no account", if not, invalid request.
        if args[0] == "no" and args[1] == "account":
            if not await player.register(None):
                await display.REG_ALREADY_NOA.send(ctx)
                return
            if was_player_registered:
                await display.REG_UPDATE_NOA.send(ctx)
                return
            await display.REG_NO_ACCOUNT.send(ctx)
            return
    await display.REG_INVALID.send(ctx)  # if any other number of args, not valid
    return
