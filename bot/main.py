# @CHECK 2.0 features OK

"""main.py

Initialize everything, attach the general handlers, run the client.
The application should be launched from this file
"""

# discord.py
from discord.ext import commands
from discord import Intents
from lib.tasks import loop

# Other modules
from asyncio import sleep
from random import seed
from datetime import datetime as dt
import logging, logging.handlers, sys, os
from time import gmtime

# General Enum and Exceptions
from modules.tools import UnexpectedError

# Display
from display import AllStrings as disp, views, ContextWrapper, InteractionContext

# Custom modules
import modules.config as cfg
import modules.roles
import modules.jaeger_calendar
import modules.loader
import modules.lobby
import modules.database
import modules.message_filter
import modules.accounts_handler
import modules.signal
import modules.stat_processor
import modules.interactions

# Classes
from match.classes.match import Match
from classes import Player, Base, Weapon

log = logging.getLogger("pog_bot")

_interactions_handler = modules.interactions.InteractionHandler(None, views.accept_button, disable_after_use=False)


def _add_main_handlers(client):
    """_add_main_handlers, private function
        Parameters
        ----------
        client : discord.py bot
            Our bot object
    """

    try:
        # help command, works in all channels
        @client.command(aliases=['h'])
        @commands.guild_only()
        async def help(ctx):
            await disp.HELP.send(ctx)
    except commands.errors.CommandRegistrationError:
        log.warning("Skipping =help registration")

    # Slight anti-spam: prevent the user to input a command if the last one isn't yet processed
    # Useful for the long processes like ps2 api, database or spreadsheet calls
    @client.event
    async def on_message(message):
        await modules.message_filter.on_message(client, message)

    # Global command error handler
    @client.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):  # Unknown command
            if modules.loader.is_all_locked():
                await disp.BOT_IS_LOCKED.send(ctx)
                return
            await disp.INVALID_COMMAND.send(ctx)
            return
        if isinstance(error, commands.errors.CheckFailure):  # Unauthorized command
            cog_name = ctx.command.cog.qualified_name
            if cog_name == "admin":
                await disp.NO_PERMISSION.send(ctx, ctx.command.name)
                return
            try:
                channel_id = cfg.channels[cog_name]
                channel_str = ""
                if isinstance(channel_id, list):
                    channel_str = "channels " + \
                        ", ".join(f'<#{id}>' for id in channel_id)
                else:
                    channel_str = f'channel <#{channel_id}>'
                # Send the use back to the right channel
                await disp.WRONG_CHANNEL.send(ctx, ctx.command.name, channel_str)
            except KeyError:  # Should not happen
                await disp.UNKNOWN_ERROR.send(ctx, "Channel key error")
            return
        # These are annoying error generated by discord.py when user input quotes (")
        bl = isinstance(error, commands.errors.InvalidEndOfQuotedStringError)
        bl = bl or isinstance(error, commands.errors.ExpectedClosingQuoteError)
        bl = bl or isinstance(error, commands.errors.UnexpectedQuoteError)
        if bl:
            # Tell the user not to use quotes
            await disp.INVALID_STR.send(ctx, '"')
            return

        try:
            original = error.original
        except AttributeError:
            original = error

        if isinstance(original, UnexpectedError):
            log.error(str(error))
            await disp.UNKNOWN_ERROR.send(ctx, original.reason)
        else:
            # Print unhandled error
            log.error(str(error))
            await disp.UNKNOWN_ERROR.send(ctx, type(original).__name__)
        raise error

    @client.event
    async def on_member_join(member):
        player = Player.get(member.id)
        if not player:
            return
        await modules.roles.role_update(player)

    @client.event
    async def on_presence_update(before, after):
        if before.status != after.status:
            await on_status_update(after)

    # Status update handler (for inactivity)
    async def on_status_update(user):
        player = Player.get(user.id)
        if not player:
            return
        await modules.roles.role_update(player)


@loop(hours=12)
async def _update_rules_message(client):
    # fetch rule message, update it
    channel = client.get_channel(cfg.channels["rules"])
    msg = await channel.fetch_message(channel.last_message_id)
    if msg.author.id == client.user.id:
        ctx = _interactions_handler.get_new_context(msg, False)
        await disp.RULES.edit(ctx)
    else:
        ctx = _interactions_handler.get_new_context(channel)
        await disp.RULES.send(ctx)


def _add_init_handlers(client):

    @_interactions_handler.callback('accept')
    async def on_rule_accept(player, interaction_id, interaction, interaction_values):
        user = interaction.user
        if modules.loader.is_all_locked():
            raise modules.interactions.InteractionNotAllowed
        # reaction to the rule message?
        p = Player.get(user.id)
        if not p:  # if new player
            # create a new profile
            p = Player(user.id, user.name)
            await modules.roles.role_update(p)
            await modules.database.async_db_call(modules.database.set_element, "users", p.id, p.get_data())
            await disp.REG_RULES.send(ContextWrapper.channel(cfg.channels["register"]),
                                      user.mention)
        elif p.is_away:
            p.is_away = False
            await modules.roles.role_update(p)
            await p.db_update("away")
            await disp.AWAY_BACK.send(ContextWrapper.channel(cfg.channels["register"]), p.mention)
        else:
            i_ctx = InteractionContext(interaction)
            await disp.REG_RULES_ALREADY.send(i_ctx)
            await modules.roles.role_update(p)

    @client.event
    async def on_ready():
        # Init lobby
        modules.lobby.init(Match, client)

        # Add all cogs
        await modules.loader.init(client)

        # Initialise matches channels
        Match.init_channels(client, cfg.channels["matches"])

        modules.roles.init(client)
        # Init signal handler
        modules.signal.init()

        _update_rules_message.start(client)

        # Update all players roles
        for p in Player.get_all_players_list():
            await modules.roles.role_update(p)
        _add_main_handlers(client)

        if not modules.lobby.get_all_names_in_lobby():
            try:
                last_lobby = modules.database.get_field("restart_data", 0, "last_lobby")
            except KeyError:
                pass
            else:
                if last_lobby:
                    for p_id in last_lobby:
                        try:
                            player = Player.get(int(p_id))
                            if player and not modules.lobby.is_lobby_stuck() and player.is_registered:
                                modules.lobby.add_to_lobby(player)
                        except ValueError:
                            pass
                    modules.database.set_field("restart_data", 0, {"last_lobby": list()})

            names = modules.lobby.get_all_names_in_lobby()
            if names:
                await disp.LB_QUEUE.send(ContextWrapper.channel(cfg.channels["lobby"]),
                                         names_in_lobby=modules.lobby.get_all_names_in_lobby())
        await modules.loader.unlock_all(client)
        log.info('Client is ready!')
        await disp.RDY.send(ContextWrapper.channel(cfg.channels["spam"]), cfg.VERSION)

    @client.event
    async def on_message(message):
        return


# TODO: testing, to be removed
def _test(client):
    from template_test_file import test_hand
    test_hand(client)


def _define_log(launch_str):
    # Logging config, logging outside the github repo
    try:
        os.makedirs('../../POG-data/logging')
    except FileExistsError:
        pass
    log_filename = '../../POG-data/logging/bot_log'
    logging.Formatter.converter = gmtime
    formatter = logging.Formatter('%(asctime)s | %(levelname)s %(message)s', "%Y-%m-%d %H:%M:%S UTC")
    # If test mode
    if launch_str == "_test":
        # Print debug
        level = logging.DEBUG
        # Print logging to console
        file_handler = logging.StreamHandler(sys.stdout)
    else:
        # Print info
        level = logging.INFO
        # Print to file, change file everyday at 12:00 UTC
        date = dt(2020, 1, 1, 12)
        file_handler = logging.handlers.TimedRotatingFileHandler(log_filename, when='midnight', atTime=date, utc=True)
    log.setLevel(level)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    class StreamToLogger(object):
        """
        Fake file-like stream object that redirects writes to a logger instance.
        """
        def __init__(self, logger, log_level=logging.INFO):
            self.logger = logger
            self.log_level = log_level
            self.linebuf = ''

        def write(self, buf):
            for line in buf.rstrip().splitlines():
                  self.logger.log(self.log_level, line.rstrip())

        def flush(self):
            pass

    # Redirect stdout and stderr to log:
    sys.stdout = StreamToLogger(log, logging.INFO)
    sys.stderr = StreamToLogger(log, logging.ERROR)

    log.addHandler(file_handler)

    # Adding discord logs
    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(logging.INFO)
    discord_logger.addHandler(file_handler)


def main(launch_str=""):

    _define_log(launch_str)

    # Init order MATTERS

    log.info("Starting init...")

    # Get data from the config file
    cfg.get_config(launch_str)

    # Set up intents
    intents = Intents.none()
    intents.guilds = True
    intents.members = True
    intents.presences = True
    intents.messages = True
    intents.message_content = True
    client = commands.Bot(command_prefix=cfg.general["command_prefix"], intents=intents)

    # Remove default help
    client.remove_command('help')

    # Initialise db and get all the registered users and all bases from it
    modules.database.init(cfg.database)
    modules.database.get_all_elements(Player.new_from_data, "users")
    modules.database.get_all_elements(Base, "static_bases")
    modules.database.get_all_elements(Weapon, "static_weapons")

    # Get Account sheet from drive
    modules.accounts_handler.init(cfg.GAPI_JSON)

    # Establish connection with Jaeger Calendar
    modules.jaeger_calendar.init(cfg.GAPI_JSON)

    # Initialise display module
    ContextWrapper.init(client)


    # Init stat processor
    modules.stat_processor.init()

    # Add init handlers
    _add_init_handlers(client)

    if launch_str == "_test":
        _test(client)

    # Run server
    # We are using our own logging system: no need for discord.py log handler
    client.run(cfg.general["token"], log_handler=None)


if __name__ == "__main__":
    # To run in 'DEV' mode, create a file called 'test' next to 'main.py'
    if os.path.isfile("test"):
        print("Running mode: 'DEV'")
        main("_test")
    else:
        print("Running mode: 'PROD', all output will be redirected to log files!\n"
              "Make sure to run in 'DEV' mode if you want debug output!"
              "Add a file called 'test' next to main.py to switch to 'DEV' mode")
        main()
