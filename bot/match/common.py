from display import AllStrings as disp, ContextWrapper
import modules.config as cfg
import discord

from modules.lobby import get_sub, get_all_names_in_lobby
from lib.tasks import Loop

from classes import Player

from logging import getLogger

log = getLogger("pog_bot")


async def check_faction(ctx, args):
    """
    Check if args contain a valid faction, if not display an error message

    :param ctx: Context used for displaying messages
    :param args: args to be examined
    :return: Message that was sent (None if no error message)
    """

    if ctx.message.mentions:
        # Don't want a mentioned player
        print(ctx.message.mentions)
        await disp.PK_FACTION_NOT_PLAYER.send(ctx)
    elif len(args) != 1:
        # All factions are in one word
        await disp.PK_NOT_VALID_FACTION.send(ctx)
    elif args[0].upper() not in cfg.i_factions:
        # Check for faction string
        await disp.PK_NOT_VALID_FACTION.send(ctx)
    else:
        return True
    return False


def switch_turn(match, team):
    """
    Change the team who can pick.

    :param match: Match object
    :param team: The team who is currently picking
    :return: Next team to pick
    """
    # Toggle turn
    team.captain.is_turn = False

    # Get the other team
    other = match.teams[team.id - 1]
    other.captain.is_turn = True
    return other


async def get_substitute(match, subbed, player=None):
    """
    Get a substitute player from lobby, return it

    :param subbed: Player who will be subbed
    :param match: Match calling this function
    :param force_player: Use this argument to force the player used for the sub. If None, pick a player from the lobby
    :return: Player found for subbing, return None if no player available
    """
    # Get a new player from the lobby, if None available, display
    was_lobbied = (not player) or (player and player.is_lobbied)
    player = get_sub(player)
    if player is None:
        await disp.SUB_NO_PLAYER.send(match.channel, subbed.mention)
        return

    Loop(coro=ping_sub_in_lobby, count=1).start(match, player, was_lobbied)

    await player.on_match_selected(match.proxy)
    return player


async def ping_sub_in_lobby(match, new_player, was_lobbied):
    if was_lobbied:
        await disp.SUB_LOBBY.send(ContextWrapper.channel(cfg.channels["lobby"]), new_player.mention, match.channel.id,
                                  names_in_lobby=get_all_names_in_lobby())
    # ctx = ContextWrapper.user(new_player.id)
    # try:
    #     await disp.MATCH_DM_PING.send(ctx, match.id, match.channel.name)
    # except discord.errors.Forbidden:
    #     log.warning(f"Player id:[{new_player.id}], name:[{new_player.name}] is refusing DMs")


async def after_pick_sub(match, subbed, force_player, ctx=None, clean_subbed=True):
    """
    Substitute a player by another one picked at random in the lobby.

    :param clean_subbed: Specify if subbed player should be cleaned
    :param ctx: Context used for displaying messages
    :param match: Match calling this function
    :param subbed: Player player to be subbed
    :return: Nothing
    """
    # Get a new player for substitution
    if not ctx:
        ctx = match.channel
    new_player = await get_substitute(match, subbed, player=force_player)
    if not new_player:
        return

    if clean_subbed:
        subbed.clean()
    team = subbed.team
    # Args for the display later
    args = [ctx, new_player.mention, subbed.mention, team.name]

    # Sub the player
    team.sub(subbed, new_player)

    # Display what happened
    if new_player.active.is_captain:
        await disp.SUB_OKAY_CAP.send(*args, match=match.proxy)
    else:
        await disp.SUB_OKAY_TEAM.send(*args, match=match.proxy)

    return new_player


def get_check_player_sync(ctx, match):
    msg = None
    player = Player.get(ctx.author.id)
    if not player or (player and not player.is_registered):
        # player not registered
        msg = disp.EXT_NOT_REGISTERED.send(ctx, cfg.channels["register"])
    elif not player.match:
        # if player not in match
        msg = disp.PK_NO_LOBBIED.send(ctx, cfg.channels["lobby"])
    elif player.match is not match.proxy:
        # if player not in the right match channel
        msg = disp.PK_WRONG_CHANNEL.send(ctx, player.match.channel.id)
    else:
        return player, msg
    return None, msg


def get_check_captain_sync(ctx, match, check_turn=True):
    """ Test if the player is in position to issue a match command
        Returns the player object if yes, None if not
    """
    a_player = None
    player, msg = get_check_player_sync(ctx, match)
    if msg:
        return a_player, msg
    if player.active is None:
        # Player is in the pick list
        msg = disp.PK_WAIT_FOR_PICK.send(ctx)
    elif not player.active.is_captain:
        # Player is not team captain
        msg = disp.PK_NOT_CAPTAIN.send(ctx)
    elif check_turn and not player.active.is_turn:
        # Not player's turn
        msg = disp.PK_NOT_TURN.send(ctx)
    else:
        a_player = player.active
    return a_player, msg


async def get_check_player(ctx, match):
    player, msg = get_check_player_sync(ctx, match)
    if msg:
        await msg
    return player


async def get_check_captain(ctx, match, check_turn=True):
    captain, msg = get_check_captain_sync(ctx, match, check_turn)
    if msg:
        await msg
    return captain
