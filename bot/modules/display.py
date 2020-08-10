"""Discord bot display module

It contains all the functions and the strings that can be outputed by the bot.

It must be used by the rest of the programm for all the messages sent by the bot.

All the strings sent can then be modified easely in this file.

Import this module and use only the following public function:

    * channelSend(stringName, id, *args, **kwargs)
    * privateSend(stringName, id, *args, **kwargs)
    * send(stringName, ctx, *args, **kwargs)
    * edit(stringName, ctx, *args, **kwargs)

"""

# discord.py
from discord import Embed, Color, TextChannel, Message, User
from discord.ext.commands import Context

# Others
from enum import Enum

# Custom modules
import modules.config as cfg
from modules.enumerations import MatchStatus
from modules.tools import isAdmin, isAlNum

_client = None


## PUBLIC:

def init(client):
    global _client
    _client = client

async def channelSend(stringName, id, *args, **kwargs):
    """ Send the message stringName in the channel identified with id, with aditional strings *args. Pass **kwargs to the embed function, if any
        Returns the message sent
    """
    channel = _client.get_channel(id)
    return await _StringEnum[stringName].value.display(channel,False,  *args, **kwargs)

async def privateSend(stringName, id, *args, **kwargs):
    """ Send the message stringName in dm to user identified with id, with aditional strings *args. Pass **kwargs to the embed function, if any
        Returns the message sent
    """
    user = _client.get_user(id)
    return await _StringEnum[stringName].value.display(user, False, *args, **kwargs)

async def send(stringName, ctx, *args, **kwargs):
    """ Send the message stringName in context ctx, with aditional strings *args. Pass **kwargs to the embed function, if any
        Returns the message sent
    """
    return await _StringEnum[stringName].value.display(ctx, False, *args, **kwargs)

async def edit(stringName, ctx, *args, **kwargs):
    """ Replaces the message ctx by the message stringName, with aditional strings *args. Pass **kwargs to the embed function, if any
        Returns the message sent
    """
    return await _StringEnum[stringName].value.display(ctx, True,  *args, **kwargs)

async def remReaction(message, user=None):
    if user == None:
        global _client
        user = _client.user
    await message.remove_reaction("✅", user)

## PRIVATE:

## Embed functions

def _registerHelp(msg):
    """ Returns register help embed
    """
    embed = Embed(
        colour=Color.blurple(),
        title='How to register?',
        description=f'You have to accept the rules in <#{cfg.discord_ids["rules"]}> to register'
    )
    embed.add_field(name='If you don\'t have a Jaeger account',
                    value='`=r no account`\n',
                    inline=False)
    embed.add_field(name='If you have a Jaeger account',
                    value='`=r charName` - If your character names have faction suffixes\n'
                          '`=r charName1 charName2 charName3` - If your character names don\'t have faction suffixes\n'
                    , inline=False)
    embed.add_field(name='Notify feature',
                    value='`=notify` - To join or leave the Notify feature\n'
                          f'When suscribed to Notify, you can be mentionned with <@&{cfg.discord_ids["notify_role"]}> by other players\n'
                    , inline=False)
    try:
        if isAdmin(msg.author):
            embed.add_field(name="Staff Commands",
                            value='`=unregister @player` - Permanently remove player profile from the system',
                            inline=False)
    except AttributeError:
        pass # if msg is from bot
    return embed

def _lobbyHelp(msg):
    """ Returns lobby help embed
    """
    embed = Embed(
        colour=Color.blurple()
    )
    embed.add_field(name='Lobby Commands',
                    value='`=j` - Join the lobby\n'
                          '`=l` - Leave the lobby\n'
                          '`=q` - See the current lobby'
                    , inline=False)
    if isAdmin(msg.author):
        embed.add_field(name="Staff Commands",
                        value='`=clear` - Clear the lobby',
                        inline=False)
    return embed

def _defaultHelp(msg):
    """ Returns fallback help embed
    """
    embed = Embed(
        colour=Color.red()
    )
    embed.add_field(name='No available command',
                    value='You are not supposed to use the bot on this channel',
                    inline=False)
    return embed

def _mapHelp(ctx):
    """ Returns map help embed
    """
    embed = Embed(
        colour=Color.blurple()
    )
    cmd = ctx.command.name
    if cmd == "pick":
        cmd = "p"
    embed.add_field(name='Map selection commands',
                    value=f'`={cmd} a base` - Display all the maps containing *a base* in their name\n'
                          f'`={cmd} 3` - Chooses the map number 3 from the selection\n'
                          f'`={cmd}` - Display the current selection or show the help\n'
                          ,
                    inline=False)
    return embed

def _matchHelp(msg):
    """ Returns match help embed
    """
    embed = Embed(
        colour=Color.blurple(),
    )
    embed.add_field(name='Match commands',
                    value='`=m` - Display the match status and team composition\n',
                    inline=False)
    embed.add_field(name='Team Captain commands',
                    value = '`=p @player` - Pick a player in your team\n'
                            '`=p VS`/`NC`/`TR` - Pick a faction\n'
                            '`=p base name` - Pick the map *base name*\n'
                            '`=ready` - To toggle the ready status of your team'
                            ,
                    inline=False)
    if isAdmin(msg.author):
        embed.add_field(name="Staff Commands",
                        value = '`=clear` - Clear the match\n'
                                '`=map base name` - Select a map',
                        inline=False)
    return embed

def _account(msg, account):
    """ Returns account message embed
    """
    desc = ""
    color = None
    if account.isDestroyed:
        desc = "This account token is no longer valid"
        color = Color.dark_grey()
    elif account.isValidated:
        desc =  f'Id: `{account.strId}`\n'+f'Username: `{account.ident}`\n'+f'Password: `{account.pwd}`\n'+'Note: This account is given to you only for the time of **ONE** match'
        color = Color.green()
    else:
        desc = "Accept the rules by reacting with a checkmark to get your account details."
        color = Color.red()
    embed = Embed(
        colour=color,
        title='Jaeger Account',
        description=f'**MUST READ: [Account usage](https://planetsideguide.com/other/jaeger/)**'
    )
    embed.add_field(name = "Logging details",value = desc,inline=False)
    embed.set_thumbnail(
        url="https://media.discordapp.net/attachments/739231714554937455/739522071423614996/logo_png.png")
    embed.set_footer(
        text='Failure to follow account usage rules can result in your suspension from ALL Jaeger events.')
    return embed

def _autoHelp(msg):
    """ Return help embed depending on current channel
    """
    if msg.channel.id == cfg.discord_ids['register']:
        return _registerHelp(msg)
    if msg.channel.id == cfg.discord_ids['lobby']:
        return _lobbyHelp(msg)
    if msg.channel.id in cfg.discord_ids['matches']:
        return _matchHelp(msg)
    return _defaultHelp(msg)

def _lobbyList(msg, namesInLobby):
    """ Returns the lobby list
    """
    embed = Embed(colour=Color.blue())
    listOfNames="\n".join(namesInLobby)
    if listOfNames == "":
        listOfNames = "Queue is empty"
    embed.add_field(name=f'Lobby: {len(namesInLobby)} / {cfg.general["lobby_size"]}',value=listOfNames,inline=False)
    return embed


def _selectedMaps(msg, sel):
    """ Returns a list of maps currently selected
    """
    embed = Embed(colour=Color.blue())
    embed.add_field(name=f"{len(sel.selection)} maps found",value=sel.toString(),inline=False)
    return embed

def _teamUpdate(arg, match):
    """ Returns the current teams
    """
    channel = None
    try:
        channel = arg.channel
    except AttributeError:
        channel = arg
    #title = ""
    if match.roundNo != 0:
        title = f"Match {match.number} - Round {match.roundNo}"
    else:
        title = f"Match {match.number}"
    embed = Embed(colour=Color.blue(), title=title, description = match.statusString)
    if match.map != None:
        embed.add_field(name = "Map",value = match.map.name,inline=False)
    for tm in match.teams:
        value = ""
        name = ""
        if tm.captain.isTurn and match.status in (MatchStatus.IS_FACTION, MatchStatus.IS_PICKING):
            value = f"Captain **[pick]**: {tm.captain.mention}\n"
        else:
            value = f"Captain: {tm.captain.mention}\n"
        value += "Players:\n"+'\n'.join(tm.playerPings)
        if match.status == MatchStatus.IS_WAITING:
            if tm.captain.isTurn:
                name = f"{tm.name} [{cfg.factions[tm.faction]}] - not ready"
            else:
                name = f"{tm.name} [{cfg.factions[tm.faction]}] - ready"
        elif tm.faction != 0:
            name = f"{tm.name} [{cfg.factions[tm.faction]}]"
        else:
            name = f"{tm.name}"
        embed.add_field(name = name,
                        value = value,
                        inline=False)
    if match.status == MatchStatus.IS_PICKING:
        embed.add_field(name=f'Remaining',value="\n".join(match.playerPings) ,inline=False)
    return embed

def _jaegerCalendar(arg):
    embed = Embed(colour=Color.blue(), title="Jaeger Calendar", url = "https://docs.google.com/spreadsheets/d/1dS8dMz8FhxnSBxPs3gfj_L5PsFzC8mtHHMlUkNYtjEI/",
    description = "Pick a base currently available in the calendar!")
    return embed

class _Message():
    """ Class for the enum to use
    """
    def __init__(self,str,ping=True,embed=None):
        self.__str = str
        self.__embedFct = embed
        self.__ping = ping


    async def display(self, ctx, edit, *args, **kwargs):
        # If is Context instead of a Message, get the Message:
        embed = None
        sendFct = None
        msg = None

        try:
            author = ctx.author
        except AttributeError:
            author = None

        # Format the string to be sent with added args
        string = self.__str.format(*args)
        # Send the string
        if self.__embedFct!=None:
            embed = self.__embedFct(ctx, **kwargs)
            # Fixes the embed mobile bug but ugly af:
            #embed.set_author(name="_____________________________")
        if edit:
            sendFct = ctx.edit
        else:
            try:
                sendFct = ctx.send
            except AttributeError:
                sendFct = _client.get_channel(ctx.channel.id).send

        if self.__ping and not author == None:
            msg = await sendFct(content=f'{author.mention} {string}', embed=embed)
        else:
            msg = await sendFct(content=string, embed=embed)
        return msg

class _StringEnum(Enum):
    """ List of different message strings available
    """
    REG_NOT_REGISTERED = _Message("You are not registered!",embed=_registerHelp)
    REG_IS_REGISTERED_OWN = _Message("You are already registered with the following Jaeger characters: `{}`, `{}`, `{}`")
    REG_IS_REGISTERED_NOA = _Message("You are already registered without a Jaeger account! If you have your own account, please re-register with your Jaeger characters.")
    REG_HELP = _Message("Registration help:",embed=_registerHelp)
    REG_NO_ACCOUNT = _Message("You successfully registered without a Jaeger account!")
    REG_INVALID = _Message("Invalid registration!",embed=_registerHelp)
    REG_CHAR_NOT_FOUND = _Message("Invalid registration! Character `{}` is not valid!",embed=_registerHelp)
    REG_NOT_JAEGER = _Message("Invalid registration! Character `{}` doesn't belong to Jaeger!",embed=_registerHelp)
    REG_ALREADY_EXIST = _Message("Invalid registration! Character `{}` is already registered by {}!")
    REG_MISSING_FACTION = _Message("Invalid registration! Can't find a {} character in your list!",embed=_registerHelp)
    REG_UPDATE_OWN = _Message("You successfully updated your profile with the following Jaeger characters: `{}`, `{}`, `{}`")
    REG_UPDATE_NOA = _Message("You successfully removed your Jaeger characters from your profile.")
    REG_WITH_CHARS = _Message("You successfully registered with the following Jaeger characters: `{}`, `{}`, `{}`")
    REG_FREEZED = _Message("You can't register while you're playing a match")
    REG_RULES = _Message("{} You have accepted the rules, you may now register", embed=_registerHelp)
    REG_NO_RULE = _Message("You have to accept the rules before registering! Check <#{}>")

    LB_OFFLINE = _Message("You can't queue if your Discord status is offline/invisible!")
    LB_ALREADY_IN = _Message("You are already in queue!")
    LB_IN_MATCH = _Message("You are already in a match!")
    LB_ADDED = _Message("You've been added to the queue!",embed=_lobbyList)
    LB_REMOVED = _Message("You've been removed from the queue!",embed=_lobbyList)
    LB_NOT_IN = _Message("You're not in queue!")
    LB_QUEUE = _Message("Current players in queue:",embed=_lobbyList)
    LB_FULL = _Message("Lobby is already full! Waiting for a match to start...")
    LB_STUCK = _Message("Lobby is full, but can't start a new match yet. Please wait...",ping=False)
    LB_STUCK_JOIN = _Message("You can't join the lobby, it is already full!")
    LB_MATCH_STARTING = _Message("Lobby full, match can start! Join <#{}> for team selection!",ping=False)
    LB_WENT_INACTIVE = _Message("{} was removed from the lobby because they went offline!",embed=_lobbyList)
    LB_CLEARED = _Message("Lobby has been cleared!", embed=_lobbyList)
    LB_EMPTY = _Message("Lobby is already empty!")

    PK_OVER = _Message("The teams are already made. You can't pick!")
    PK_NO_LOBBIED = _Message("You must first queue and wait for a match to begin. Check <#{}>")
    PK_WAIT_FOR_PICK = _Message("You can't pick! Wait for a Team Captain to pick you")
    PK_WRONG_CHANNEL = _Message("You are in the wrong channel! Check <#{}> instead")
    PK_NOT_TURN = _Message("It's not your turn!")
    PK_NOT_CAPTAIN = _Message("You are not Team Captain!")
    PK_SHOW_TEAMS = _Message("Match status:",embed=_teamUpdate)
    PK_HELP = _Message("Picking help:", embed=_matchHelp)
    PK_NO_ARG = _Message("@ mention a player to pick!", embed=_matchHelp)
    PK_TOO_MUCH = _Message("You can't pick more than one player at the same time!")
    PK_INVALID = _Message("You can't pick that player!")
    PK_OK = _Message("Player picked! {} your turn, pick a player!",embed=_teamUpdate, ping=False)
    PK_OK_2 = _Message("Player picked!", ping=False)
    PK_LAST = _Message("Assigned {} to {}!")
    PK_OK_FACTION = _Message("Teams are ready! {} pick a faction!",embed=_teamUpdate, ping=False)
    PK_NOT_VALID_FACTION = _Message("Incorrect input! Pick a valid faction!", embed=_matchHelp)
    PK_FACTION_OK = _Message("{} chose {}!", ping=False)
    PK_FACTION_ALREADY = _Message("Faction already picked by the other team!")
    PK_FACTION_OK_NEXT = _Message("{} chose {}! {} pick a faction!", ping=False)
    PK_FACTION_NOT_PLAYER = _Message("Pick a faction, not a player!", embed=_matchHelp)
    PK_WAIT_MAP = _Message("{} {} Pick an available map with `=p base name`!", ping=False, embed=_jaegerCalendar)
    PK_MAP_OK_CONFIRM = _Message("Picked {}! {} confirm with `=p confirm` if you agree")
    PK_NO_MAP = _Message("No map selected!")

    EXT_NOT_REGISTERED = _Message("You are not registered! Check <#{}>")
    UNKNOWN_ERROR = _Message("Something unexpected happened! Please try again or contact staff if it keeps happening.\nDetails:*{}*")
    STOP_SPAM = _Message("Please avoid spamming!")
    HELP = _Message("Available commands:",embed=_autoHelp)
    INVALID_COMMAND = _Message("Invalid command! Type `=help` for the list of available commands.")
    WRONG_USAGE = _Message("Wrong usage of the command `={}`!")
    WRONG_CHANNEL = _Message("The command `={}` can only be used in {}")
    WRONG_CHANNEL_2 = _Message("The command `={}` can't be used in {}")
    NO_PERMISSION = _Message("The command `={}` can only be used by staff members!")
    CHANNEL_INIT = _Message("`Bot init`: Correctly hooked in channel <#{}>")
    INVALID_STR = _Message("You entered an invalid caracter! `{}`")

    BOT_UNLOCKED = _Message("Unlocked!")
    BOT_LOCKED = _Message("Locked!")
    BOT_IS_LOCKED = _Message("Unlock the bot before using this command!")
    BOT_ALREADY = _Message("Already {}!")
    BOT_VERSION = _Message("Version `{}`, locked: `{}`")

    MATCH_INIT = _Message("{}\nMatch is ready, starting team selection...")
    MATCH_SHOW_PICKS = _Message("Captains have been selected, {} choose a player",embed=_teamUpdate)
    MATCH_MAP_AUTO = _Message("Match will be on **{}**", ping=False)
    MATCH_CONFIRM = _Message("{} {} Type `=ready` when your team is inside their sundy, ready to start", embed=_teamUpdate)
    MATCH_NOT_READY = _Message("You can't use command {}, the match is not ready to start!")
    MATCH_TEAM_READY = _Message("{} is now ready!", embed=_teamUpdate)
    MATCH_TEAM_UNREADY = _Message("{} is no longer ready!", embed=_teamUpdate)
    MATCH_STARTING_1 = _Message("Everyone is ready, round {} is starting in {} seconds!\nAll players will be pinged on round start")
    MATCH_STARTING_2 = _Message("Round {} is starting in {} seconds!")
    MATCH_STARTED = _Message("{}\n{}\nRound {} is starting now!")
    MATCH_NO_MATCH = _Message("Can't use command `={}`, no match is happening here!")
    MATCH_ALREADY_STARTED = _Message("Can't use command `={}` now!")
    MATCH_CLEARED = _Message("Successfully cleared!")
    MATCH_PLAYERS_NOT_READY = _Message("Can't get {} ready, {} did not accept their Jaeger accounts", ping=False)
    MATCH_CLEAR = _Message("Clearing match...",ping=False)
    MATCH_MAP_SELECTED = _Message("Successfully selected **{}**")
    MATCH_ROUND_OVER = _Message("{}\n{}\nRound {} is over!")
    MATCH_OVER = _Message("The match is over!\nClearing channel...")
    MATCH_ALREADY = _Message("The match is already started!")
    MATCH_SWAP = _Message("Swap sundy placement for the next round!")

    MAP_HELP = _Message("Here is how to choose a map:", embed = _mapHelp)
    MAP_TOO_MUCH = _Message("Too many maps found! Try to be more precise")
    MAP_NOT_FOUND = _Message("Couldn't find a result for your search!")
    MAP_DISPLAY_LIST = _Message("Here are the maps found:", embed=_selectedMaps)
    MAP_SELECTED = _Message("The current map is **{}**")

    ACC_NOT_ENOUGH = _Message("Not enough accounts are available for this match!\n**Match has been canceled!**")
    ACC_UPDATE = _Message("", ping=False,embed=_account)
    ACC_ERROR = _Message("One of the PIL pug accounts is invalid: `{}`")
    ACC_SENT = _Message("**Successfully sent jaeger accounts  in DMs!**")
    ACC_SENDING = _Message("Loading Jaeger accounts...")
    ACC_OVER = _Message("Match is over, please log out of your Jaeger account!")

    NOTIFY_REMOVED = _Message("You left Notify!")
    NOTIFY_ADDED = _Message("You joined Notify!")

    NOT_CODED = _Message("The rest is not yet coded, work in progress. Clearing match...")

    RM_MENTION_ONE = _Message("Invalid request! Mention one player to be removed!")
    RM_NOT_IN_DB = _Message("Can't find this player in the database!")
    RM_OK = _Message("Player successfully removed from the system!")
    RM_IN_MATCH = _Message("Can't remove a player who is in match!")
    RM_LOBBY = _Message("{} have been removed by staff!",embed=_lobbyList)