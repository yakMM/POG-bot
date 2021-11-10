from enum import Enum
from display import embeds, views

from .classes import Message, ContextWrapper

class AllStrings(Enum):
    """ List of different message strings available
    """

    REG_NOT_REGISTERED = Message("You are not registered!", embed=embeds.register_help)
    REG_STATUS = Message(None, embed=embeds.register_status)
    REG_ALREADY_OWN = Message("You are already registered with the following Jaeger characters: `{}`, `{}`, `{}`")
    REG_ALREADY_NOA = Message("You are already registered without a Jaeger account! If you have your own "
                              "account, please re-register with your Jaeger characters.")
    REG_HELP = Message("Registration help:", embed=embeds.register_help)
    REG_NO_ACCOUNT = Message("You successfully registered without a Jaeger account!")
    REG_INVALID = Message("Invalid registration!")
    REG_CHAR_NOT_FOUND = Message("Invalid registration! Character `{}` is not valid!")
    REG_NOT_JAEGER = Message("Invalid registration! Character `{}` doesn't belong to Jaeger!")
    REG_ALREADY_EXIST = Message("Invalid registration! Character `{}` is already registered by {}!")
    REG_MISSING_FACTION = Message("Invalid registration! Can't find a {} character in your list!")
    REG_UPDATE_OWN = Message("You successfully updated your profile with the following Jaeger characters:"
                             " `{}`, `{}`, `{}`")
    REG_UPDATE_NOA = Message("You successfully removed your Jaeger characters from your profile.")
    REG_WITH_CHARS = Message("You successfully registered with the following Jaeger characters: `{}`, `{}`, `{}`")
    REG_FROZEN = Message("You can't register while you're playing a match!")
    REG_RULES = Message("{} You have accepted the rules, you may now register", embed=embeds.register_help)

    LB_ALREADY_IN = Message("You are already in queue!")
    LB_IN_MATCH = Message("You are already in a match!")
    LB_ADDED = Message("You've been added to the queue!", embed=embeds.lobby_list)
    LB_REMOVED = Message("You've been removed from the queue!", embed=embeds.lobby_list)
    LB_NOT_IN = Message("You're not in queue!")
    LB_QUEUE = Message("Current players in queue:", embed=embeds.lobby_list)
    LB_FULL = Message("Lobby is already full! Waiting for a match to start...")
    LB_STUCK = Message("Lobby is full, but can't start a new match yet. Please wait...", ping=False)
    LB_STUCK_JOIN = Message("You can't join the lobby, it is already full!")
    LB_MATCH_STARTING = Message("Lobby full, match can start! Join <#{}> for team selection!", ping=False,
                                embed=embeds.join_ts)
    LB_WARNING = Message("{} you will be timed out of the lobby soon! Use `=reset` or react below to remain in the queue!")
    LB_TOO_LONG = Message("{} was removed from the lobby by timeout!", embed=embeds.lobby_list)
    LB_CLEARED = Message("Lobby has been cleared!", embed=embeds.lobby_list)
    LB_EMPTY = Message("Lobby is already empty!")
    LB_NOTIFY = Message("{} queue is almost full ({}/{}), join to start a match!")
    LB_GET = Message("Restore the lobby with `=lobby restore {}`")
    LB_SAVE = Message("Lobby status saved, will be restored on next restart!")
    LB_REFRESHED = Message("You have reset your queue timeout!")

    PK_OVER = Message("The teams are already made. You can't pick!")
    PK_NO_LOBBIED = Message("You must first queue and wait for a match to begin. Check <#{}>")
    PK_WAIT_FOR_PICK = Message("You can't do that! Wait for a Team Captain to pick you!")
    PK_WRONG_CHANNEL = Message("You are in the wrong channel! Check <#{}> instead")
    PK_NOT_TURN = Message("It's not your turn!")
    PK_NOT_CAPTAIN = Message("You are not Team Captain!")
    PK_SHOW_TEAMS = Message("Match status:", embed=embeds.team_update, ping=False)
    PK_PLAYERS_HELP = Message("Waiting for {} to pick a player with `=p @mention`", ping=False)
    PK_NO_ARG = Message("@ mention a player to pick!")
    PK_TOO_MUCH = Message("You can't pick more than one player at the same time!")
    PK_INVALID = Message("You can't pick that player!")
    PK_OK = Message("Player picked! {} your turn, pick a player!", embed=embeds.team_update, view=views.players_buttons, ping=False)
    PK_P_OK = Message("Picked {}! {} your turn, pick a player!",
                    embed=embeds.team_update, view=views.players_buttons,
                    ping=False)
    PK_OK_2 = Message("Player picked!", ping=False)
    PK_P_OK_2 = Message("Picked {}!", ping=False)
    PK_LAST = Message("Assigned {} to {}!", embed=embeds.team_update)
    PK_OK_FACTION = Message("Teams are ready! {} pick a faction with `=pick` `tr`/`vs`/`nc` or by reacting below!",
                            ping=False)
    PK_NOT_VALID_FACTION = Message("Incorrect input!")
    PK_FACTION_OK = Message("{} chose {}!", ping=False)
    PK_FACTION_ALREADY = Message("Your team is already {}!")
    PK_FACTION_OTHER = Message("Faction already picked by the other team!")
    PK_FACTION_OK_NEXT = Message("{} chose {}! {} pick a faction with `=pick` `tr`/`vs`/`nc` or by reacting below!",
                                 ping=False)
    PK_FACTION_CHANGED = Message("{} changed to {}!", ping=False)
    PK_FACTION_NOT_PLAYER = Message("Pick a faction, not a player!")
    PK_FACTION_INFO = Message("Captains can change faction with `=pick` `tr`/`vs`/`nc`!")
    PK_FACTION_HELP = Message("Waiting for {} to pick a faction with `=pick` `tr`/`vs`/`nc` or by reacting below!",
                              ping=False)
    PK_BASING_INFO = Message("Waiting for captains to pick a base with `=base`!\n"
                             "Captains can change faction with `=pick` `tr`/`vs`/`nc`!")

    EXT_NOT_REGISTERED = Message("You are not registered! Check <#{}>")
    UNKNOWN_ERROR = Message("Something unexpected happened! Please try again or contact staff if it keeps happening.\n"
                            "Details: *{}*")
    STOP_SPAM = Message("Previous request is being processed... Please avoid spamming!")
    HELP = Message("Available commands:", embed=embeds.auto_help)
    INVALID_COMMAND = Message("Invalid command! Type `=help` for the list of available commands.")
    WRONG_USAGE = Message("Wrong usage of the command `={}`!")
    WRONG_CHANNEL = Message("The command `={}` can only be used in {}")
    WRONG_CHANNEL_2 = Message("The command `={}` can't be used in {}")
    NO_PERMISSION = Message("The command `={}` can only be used by staff members!")
    CHANNEL_INIT = Message("`Bot init`: Correctly hooked in channel <#{}>")
    INVALID_STR = Message("You entered an invalid argument! `{}`")
    API_ERROR = Message("Could not reach Planetside2 API, try again later!")
    API_READY_ERROR = Message("Could not reach Planetside2 API, player online check ignored!", ping=False)
    API_SCORE_ERROR = Message("Match {}, round {}: Could not reach Planetside2 API, no scores for this round!")
    PUBLISH_ERROR = Message("Match {}, round {}: Could not publish score image, no scores for this round!")
    GLOBAL_INFO = Message("Here is what's going on in POG at the moment:", embed=embeds.global_info)
    CHECK_ACCOUNT = Message("Your account password may have been flipped!\n"
                            "Re-register in <#{}> to confirm you still have access to it!", embed=embeds.flip_accounts)
    RDY = Message("Bot just started and is now ready. Version `{}`")
    STOP = Message("Bot shutting down! Saving state...")
    SPAM_CLEARED = Message("Cleared the spam list!")
    SPAM_DEBUG = Message("Here are the players in the spam filter:{}")
    CONFIRM_NOT_CAPTAIN = Message("You can't accept! {} should do it!")
    CONFIRM_NOTHING = Message("Nothing to accept!")
    DECLINE_NOTHING = Message("Nothing to decline!")
    DECLINE_NOT_CAPTAIN = Message("You can't decline! {} should do it!")
    CONFIRM_DECLINE = Message("You declined the request!")
    CONFIRM_CANCELED = Message("You canceled the request!")
    CANCEL_NOTHING = Message("Nothing to cancel!")
    CANCEL_NOT_CAPTAIN = Message("You can't cancel this request!")
    NO_RULE = Message("You have to accept the rules before using `{}`! Check <#{}>")
    DISPLAY_STATS = Message("Here are your POG stats:", embed=embeds.player_stats)

    BOT_UNLOCKED = Message("Unlocked!")
    BOT_LOCKED = Message("Locked!")
    BOT_IS_LOCKED = Message("Bot is locked!")
    BOT_ALREADY = Message("Already {}!")
    BOT_VERSION = Message("Version `{}`, locked: `{}`")
    BOT_FROZEN = Message("Channel frozen!")
    BOT_UNFROZEN = Message("Channel unfrozen!")
    BOT_BP_OFF = Message("Ingame status check is now enabled!")
    BOT_BP_ON = Message("Ingame status check is now disabled!")
    BOT_DM = Message(None, embed=embeds.direct_message)
    BOT_DM_RECEIVED = Message("Thanks for your message, it was forwarded to POG staff!", ping=False)
    BOT_RELOAD = Message("{} reloaded!")
    BOT_U_DUMB = Message("That's not really nice, I'm doing my best to bring 24/7 Jaeger matches in a friendly "
                         "environment and all the rewards that I get are insults and wickedness :(")

    CAP_WAITING = Message("Waiting for captain(s), use `=captain volunteer` or react below if you want to be one",
                          ping=False, embed=embeds.team_update, view=views.volunteer_button)
    CAP_AUTO_ANNOUNCE = Message("Captains will be automatically suggested in 1 minute!")
    CAP_OK = Message("{} will be captain for {}!", ping=False)
    CAP_AUTO = Message("{} has been designated as captain for {}\n"
                       "Accept or decline with `=captain accept/decline` or by reacting below!")
    CAP_HELP = Message("Here are the available captain commands:", embed=embeds.captain_help)
    CAP_ALREADY = Message("You can't do that! You are already a team captain!")
    CAP_ACCEPT_NO = Message("You can't do that! Volunteer if you want to be captain!")
    CAP_DENY_NO = Message("You can't do that, you were not designated as team captain!")
    CAP_DENY_OK = Message("You declined the team captain role!")
    CAP_NEW = Message("{} is the new captain for {}!")

    MATCH_DM_PING = Message("POG match {} is starting! Please join `{}` channel in the Jaeger Events discord!", ping=False)
    MATCH_INIT = Message("{}\nMatch is ready, starting team selection...")
    MATCH_SHOW_PICKS = Message("Captains have been selected, {} choose a player", embed=embeds.team_update, view=views.players_buttons, ping=False)
    MATCH_BASE_AUTO = Message("Match will be on **{}**", ping=False)
    MATCH_CONFIRM = Message("{} {} Type `=ready` or react below when your team is inside their sunderer, ready to start",
                            embed=embeds.team_update)
    MATCH_TEAM_READY = Message("{} is now ready!", embed=embeds.team_update)
    MATCH_TEAM_UNREADY = Message("{} is no longer ready!", embed=embeds.team_update)
    MATCH_STARTING_1 = Message("Everyone is ready, round {} is starting in {} seconds!\nAll players will be pinged on "
                               "round start")
    MATCH_STARTING_2 = Message("Round {} is starting in {} seconds!")
    MATCH_STARTED = Message("{}\n{}\nRound {} is starting now!")
    MATCH_NO_MATCH = Message("Can't use command `={}`, no match is happening here!")
    MATCH_NO_COMMAND = Message("Can't use command `={}` now!")
    MATCH_NO_COMMAND_READY = Message("Can't use command `={}: your team is ready!")
    MATCH_CLEARED = Message("Successfully cleared!")
    MATCH_PLAYERS_NOT_READY = Message("Can't get {} ready, {} did not accept their Jaeger accounts", ping=False)
    MATCH_PLAYERS_OFFLINE = Message("Can't get {} ready, {} {} not online in game!", ping=False,
                                    embed=embeds.offline_list)
    MATCH_CLEAR = Message("Clearing match...", ping=False)
    MATCH_ROUND_OVER = Message("{}\n{}\nRound {} is over!")
    MATCH_OVER = Message("The match is over!\nClearing...")
    MATCH_SWAP = Message("Swap sundy placement for the next round!")
    MATCH_CHANNEL_OVER = Message("Locking channel until next match...")
    MATCH_CHECK_CHANGED = Message("{} check is now {}")

    BASE_HELP = Message("Here is how to choose a base:", embed=embeds.base_help)
    BASE_TOO_MUCH = Message("Too many bases found! Try to be more precise")
    BASE_NOT_FOUND = Message("Couldn't find a result for your search!")
    BASE_ON_SELECT = Message("Successfully selected **{}**", embed=embeds.base_display)
    BASE_SHOW_LIST = Message("Select a base with `=base Name`", ping=False, view=views.bases_selection)
    BASE_SELECTED = Message("This match will be played on **{}**:", embed=embeds.base_display)
    BASE_DISPLAY = Message("Base navigator:", ping=False, embed=embeds.base_display)
    BASE_BOOKED = Message("{} WARNING: **{}** seems unavailable. Please check occupation "
                          "before confirming this base.", ping=False, embed=embeds.jaeger_calendar)
    # BASE_ADDED = Message("Added {} to the base pool")
    # BASE_REMOVED = Message("Removed {} from the base pool")
    BASE_CALENDAR = Message("{} Pick an available base!", ping=False, embed=embeds.jaeger_calendar)
    BASE_NO_BASE = Message("No base yet selected!")
    BASE_NO_BASE_WAITING = Message("Waiting for captains to pick a base...")
    BASE_OK_CONFIRM = Message("Picked **{}**! {} accept if you agree!", view=views.validation_buttons)
    BASE_NO_CHANGE = Message("It's not possible to change the match base anymore!")
    BASE_NO_READY = Message("Can't change the base if a team is ready!")

    ACC_NOT_ENOUGH = Message("Not enough accounts are available for this match!\n**Match has been canceled!**")
    ACC_ERROR = Message("Error when giving out Jaeger accounts!\n**Match has been canceled!**")
    ACC_UPDATE = Message(None, ping=False, embed=embeds.account)
    ACC_STAFF = Message("{}, couldn't send the account to {}, please send it manually...", ping=False,
                        embed=embeds.account)
    ACC_SENT = Message("**Successfully sent all jaeger accounts!**")
    ACC_SENDING = Message("Loading Jaeger accounts...")
    ACC_OVER = Message("Match is over, please log out of your Jaeger account!", ping=False)
    ACC_CLOSED = Message("{}'s DMS are locked, couldn't send them a Jaeger account after 3 retries!\nSending the "
                         "account to staff instead.")
    ACC_LOG = Message("Player [name:{}], [id:{}] will receive {}")
    ACC_GIVING = Message("Sent a Jaeger account for {}!", ping=False)

    NO_DATA = Message("No data for this id!")
    ACCOUNT_USAGE = Message("Here is the POG account usage for this user:", embed=embeds.usage)
    DISPLAY_USAGE = Message("<@{}> played {} POG match{} in the last {}. \n(since {})", ping=False)
    PSB_USAGE = Message("Here is the participation for {}, for 8 weeks leading up to {}:", ping=False, embed=embeds.psb_usage)

    NOTIFY_REMOVED = Message("You left Notify!")
    NOTIFY_ADDED = Message("You joined Notify!")

    NOT_CODED = Message("The rest is not yet coded, work in progress. Clearing match...")

    RM_MENTION_ONE = Message("Invalid request! @ mention one player!")
    RM_NOT_IN_DB = Message("Can't find player in the database!")
    RM_OK = Message("Player successfully removed from the system!")
    RM_IN_MATCH = Message("Can't remove a player who is in match!")
    RM_LOBBY = Message("{} have been removed by staff!", embed=embeds.lobby_list)
    RM_NOT_LOBBIED = Message("This player is not in queue!")
    RM_TIMEOUT = Message("{} will be muted from POG until {}!", ping=False)
    RM_TIMEOUT_FREE = Message("{} is no longer muted!", ping=False)
    RM_TIMEOUT_ALREADY = Message("Can't do that, player is not muted!")
    RM_TIMEOUT_HELP = Message("Command usage:", embed=embeds.timeout_help)
    RM_TIMEOUT_INVALID = Message("Invalid use of the command!", embed=embeds.timeout_help)
    RM_TIMEOUT_INFO = Message("Player is muted until {}!")
    RM_TIMEOUT_NO = Message("Player is not muted!")
    RM_NAME_CHANGED = Message("Changed {}'s name to `{}`!", ping=False)
    RM_NAME_INVALID = Message("Rename failed! The name contains invalid characters!")
    RM_CAP = Message("Invalid request! {} is a team captain!", ping=False)

    MUTE_SHOW = Message("You are muted from POG until {}!")
    MUTE_FREED = Message("You are no longer muted from POG!")

    SC_ILLEGAL_WE = Message("{} used {} during match {}! This weapon is banned! Ignoring {} kill(s)...")
    SC_PLAYERS_STRING = Message("Here is player data for squittal script:\n{}\n")
    SC_PLAYERS_STRING_DISC = Message("Here is player data for squittal script:\n{}\n"
                                     "Disclaimer: This info might still change before the match actually starts!")
    SC_RESULT_HALF = Message("Match {} - **halftime**")
    SC_RESULT = Message("Match {}")

    SUB_NO = Message("This player can't be subbed!")
    SUB_NOT_OK = Message("Can't sub a player at this stage!")
    SUB_NO_PLAYER = Message("Subbing {}: no player is available to substitute!")
    SUB_OKAY_TEAM = Message("{} replaced {} in {}", ping=False, embed=embeds.team_update)
    SUB_OKAY_CAP = Message("{} replaced {} as {}'s captain", ping=False, embed=embeds.team_update)
    SUB_OKAY = Message("{} replaced {}!", ping=False, embed=embeds.team_update)
    SUB_LOBBY = Message("{} you have been designated as a substitute, join <#{}>!", embed=embeds.lobby_list)
    SUB_OK_CONFIRM = Message("Subbing {}! {} accept if you agree!", ping=False)
    SUB_ONLY_ADMIN = Message("Only staff can sub players before captains are selected!")

    SWAP_OK = Message("Successfully swapped {} and {}", ping=False, embed=embeds.team_update)
    SWAP_MENTION_2 = Message("Invalid request! @ mention two players to swap!")
    SWAP_NO = Message("{} can't be swapped!", ping=False)
    SWAP_SAME_TEAM = Message("Invalid request! Can't swap two players of the same team!", ping=False)
    SWAP_OK_CONFIRM = Message("Swapping players! {} accept if you agree! (use `=swap accept/decline` or react below)")

    BENCH_MENTION = Message("Invalid request! @ mention one player to bench!")
    BENCH_NO = Message("{} can't be benched!", ping=False)
    BENCH_OK_CONFIRM = Message("Benching player! {} accept if you agree!", view=views.validation_buttons)
    UNBENCH_OK_CONFIRM = Message("Un-benching player! {} accept if you agree!", view=views.validation_buttons)
    BENCH_OK = Message("Successfully benched {}!", ping=False, embed=embeds.team_update)
    UNBENCH_OK = Message("Successfully un-benched {}!", ping=False, embed=embeds.team_update)
    BENCH_ALREADY = Message("Player is already benched!", ping=False)
    BENCH_NOT = Message("Player is not benched!", ping=False)
    BENCH_ALL = Message("Can't bench {}, no active player left in the team!")

    async def send(self, ctx, *args, **kwargs):
        """
        Send the message

        :param ctx: context.
        :param args: Additional strings to format the main string with.
        :param kwargs: Keywords arguments to pass to the embed function.
        :return: The message sent.
        """
        if not isinstance(ctx, ContextWrapper):
            ctx = ContextWrapper.wrap(ctx)
        kwargs = self.value.get_elements(ctx, string_args=args, ui_kwargs=kwargs)
        return await ctx.send(kwargs)

    async def edit(self, msg, *args, **kwargs):
        """
        Edit the message

        :param msg: Message to edit.
        :param args: Additional strings to format the main string with.
        :param kwargs: Keywords arguments to pass to the embed function.
        :return: The message edited.
        """
        kwargs = self.value.get_elements(msg, string_args=args, ui_kwargs=kwargs)
        return await msg.edit(**kwargs)

    async def image_send(self, ctx, image_path, *args):
        if not isinstance(ctx, ContextWrapper):
            ctx = ContextWrapper.wrap(ctx)
        kwargs = self.value.get_elements(ctx, string_args=args, image_path=image_path)
        return await ctx.send(kwargs)


