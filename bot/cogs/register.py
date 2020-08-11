# discord.py
from discord.ext import commands

# Custom classes
from classes.players import Player, getPlayer

# Custom modules
import modules.config as cfg
from modules.enumerations import PlayerStatus
from modules.display import channelSend, send
from modules.tools import isAlNum
from modules.exceptions import UnexpectedError, ElementNotFound, CharNotFound, CharInvalidWorld, CharMissingFaction, CharAlreadyExists
from modules.database import update as dbUpdate


class registerCog(commands.Cog, name='register'):
    """
    Register cog, handle the commands from register channel
    """

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('Register Cog is online')
        return # we don't display a message on each restart
        try:
            await channelSend("CHANNEL_INIT", cfg.discord_ids["register"], cfg.discord_ids["register"])
        except AttributeError:
            raise UnexpectedError("Invalid channel id!")

    """
    Registered Commands:

    =register
    """

    async def cog_check(self, ctx): # Check if right channel
        return ctx.channel.id == cfg.discord_ids['register']


    @commands.command(aliases=['r'])
    @commands.guild_only()
    async def register(self, ctx, *args):
        if len(ctx.message.mentions) != 0: # Don't want a mention here
            await send("REG_INVALID",ctx)
            return
        try:
            player = getPlayer(ctx.author.id)
        except ElementNotFound:
            await send("REG_NO_RULE", ctx, cfg.discord_ids["rules"])
            return

        msg = await _register(player, ctx, args)

    @commands.command()
    @commands.guild_only()
    async def notify(self, ctx):
        member = ctx.author
        notify = member.guild.get_role(cfg.discord_ids["notify_role"])
        registered = member.guild.get_role(cfg.discord_ids["registered_role"])
        if notify in member.roles:
            await member.add_roles(registered)
            await member.remove_roles(notify)
            await send("NOTIFY_REMOVED", ctx)
        else:
            await member.add_roles(notify)
            await member.remove_roles(registered)
            await send("NOTIFY_ADDED", ctx)

def setup(client):
    client.add_cog(registerCog(client))

async def _register(player, ctx, args):
    """
    Set player's ingame name(s).

    Check if inputed names are valid ingame names and find the id for each name.
    Check the faction of each name and registered the name for the player

    Parameters:
    ingameNames (str, list of str): If a list, will add each name one by one. If a string, will add the faction suffixes automatically.
    """
    if player.status == PlayerStatus.IS_PLAYING: # Can't register if already playing
        await send("REG_FREEZED",ctx)
        return
    for name in args:
        if not isAlNum(name): # Char names are only alphanum names
            await send("INVALID_STR",ctx, name)
            return
    if len(args) == 0: # If user did not input any arg, display their current registration status
        if player.status == PlayerStatus.IS_NOT_REGISTERED:
            await send("REG_NOT_REGISTERED",ctx)
            return
        if player.hasOwnAccount:
            await send("REG_IS_REGISTERED_OWN",ctx,*player.igNames)
            return
        await send("REG_IS_REGISTERED_NOA",ctx)
        return
    wasPlayerRegistered = player.status != PlayerStatus.IS_NOT_REGISTERED # store previous status
    if len(args) == 1 or len(args) == 3: # if 1 or 3 args
        if len(args) == 1 and args[0]=="help": # =r help displays hel^p
            await send("REG_HELP",ctx)
            return
        try:
            if not await player.register(args): # player.register return a boolean: hasTheProfileBeenUpdated
                await send("REG_IS_REGISTERED_OWN",ctx,*player.igNames) # if no update, say "you are already registered etc"
                return
            await dbUpdate(player) # push update to db
            if wasPlayerRegistered:
                await send("REG_UPDATE_OWN",ctx,*player.igNames)
                return
            await send("REG_WITH_CHARS",ctx,*player.igNames)
            return
        except CharNotFound as e: # if problems with chars
            await send("REG_CHAR_NOT_FOUND",ctx,e.char)
            return
        except CharInvalidWorld as e:
            await send("REG_NOT_JAEGER",ctx,e.char)
            return
        except CharMissingFaction as e:
            await send("REG_MISSING_FACTION",ctx,e.faction)
            return
        except CharAlreadyExists as e:
            await send("REG_ALREADY_EXIST",ctx,e.char, f"<@{e.id}")
            return
        except UnexpectedError:
            await send("UNKNOWN_ERROR",ctx,"Reg error, check logs")
            return
    if len(args) == 2: # if 2 args, it should be "no account", if not, invalid request. Again, check if update and push db if that's the case
        if args[0]=="no" and args[1]=="account":
            if not await player.register(None):
                await send("REG_IS_REGISTERED_NOA",ctx)
                return
            await dbUpdate(player)
            if wasPlayerRegistered:
                await send("REG_UPDATE_NOA",ctx)
                return
            await send("REG_NO_ACCOUNT",ctx)
            return
    await send("REG_INVALID",ctx) # if any other number of args, not valid
    return