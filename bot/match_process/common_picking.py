from display.strings import AllStrings as disp
from display.classes import ContextWrapper
from modules.lobby import get_sub, get_all_names_in_lobby
import modules.config as cfg
from lib.tasks import Loop

from logging import getLogger

log = getLogger("pog_bot")


async def get_substitute(ctx, match):
    # Get a new player from the lobby, if None available, display
    new_player = get_sub()
    if new_player is None:
        await disp.SUB_NO_PLAYER.send(ctx, match.channel)
        return

    # We have a player. Ping them in the lobby and change their status
    Loop(coro=ping_sub_in_lobby, count=1).start(match, new_player)

    new_player.on_match_selected(match.proxy)
    return new_player


async def ping_sub_in_lobby(match, new_player):
    await disp.SUB_LOBBY.send(ContextWrapper.channel(cfg.channels["lobby"]), new_player.mention, match.channel.id,
                              names_in_lobby=get_all_names_in_lobby())


def switch_turn(process, team):
    """ Change the team who can pick.

        Parameters
        ----------
        team : Team
            The team who is currently picking.

        Returns
        -------
        other : Team
            The other team who will pick now
    """
    # Toggle turn
    team.captain.is_turn = False

    # Get the other team
    other = process.match.teams[team.id - 1]
    other.captain.is_turn = True
    process.picking_captain = other.captain
    return other


async def after_pick_sub(ctx, match, subbed):
    """ Substitute a player by another one picked at random \
        in the lobby.

        Parameters
        ----------
        subbed : Player
            Player to be substituted
    """
    # Get a new player for substitution
    new_player = await get_substitute(ctx, match)
    if not new_player:
        return

    # Get active version of the player and clean the player object
    a_sub = subbed.active
    subbed.on_player_clean()
    team = a_sub.team
    # Args for the display later
    args = [match.channel, new_player.mention, a_sub.mention, team.name]

    # Sub the player
    team.sub(a_sub, new_player)

    # Display what happened
    if new_player.active.is_captain:
        await disp.SUB_OKAY_CAP.send(*args, match=match.proxy)
    else:
        await disp.SUB_OKAY_TEAM.send(*args, match=match.proxy)


async def check_faction(ctx, args):
    # Don't want a mentioned player
    if len(ctx.message.mentions) != 0:
        return await disp.PK_FACTION_NOT_PLAYER.send(ctx)

    # All factions are in one word
    if len(args) != 1:
        return await disp.PK_NOT_VALID_FACTION.send(ctx)

    # Check for faction string
    if args[0].upper() not in cfg.i_factions:
        return await disp.PK_NOT_VALID_FACTION.send(ctx)


async def faction_change(ctx, captain, args, match):
    if await check_faction(ctx, args):
        return

    faction = cfg.i_factions[args[0].upper()]
    team = captain.team
    other = match.teams[team.id - 1]

    if team.faction == faction:
        await disp.PK_FACTION_ALREADY.send(ctx, cfg.factions[faction])
    elif other.faction == faction:
        await disp.PK_FACTION_OTHER.send(ctx)
    else:
        team.faction = faction
        await disp.PK_FACTION_CHANGED.send(ctx, team.name, cfg.factions[faction])
