from display.strings import AllStrings as disp
from display.classes import ContextWrapper
from modules.lobby import get_sub, get_all_names_in_lobby
import modules.config as cfg
from lib.tasks import Loop
from .captain_validator import CaptainValidator
from classes import Player

from logging import getLogger

import modules.roles as roles

log = getLogger("pog_bot")


async def get_substitute(match, subbed, force_player=None):
    """
    Get a substitute player from lobby, return it

    :param subbed: Player who will be subbed
    :param match: Match calling this function
    :return: Player found for subbing
    """
    # Get a new player from the lobby, if None available, display
    if not force_player:
        new_player = get_sub()
        if new_player is None:
            await disp.SUB_NO_PLAYER.send(match.channel, subbed.mention)
            return
    else:
        new_player = force_player

    Loop(coro=ping_sub_in_lobby, count=1).start(match, new_player)

    new_player.on_match_selected(match.proxy)
    return new_player


async def ping_sub_in_lobby(match, new_player):
    if new_player.is_lobbied:
        await disp.SUB_LOBBY.send(ContextWrapper.channel(cfg.channels["lobby"]), new_player.mention, match.channel.id,
                                  names_in_lobby=get_all_names_in_lobby())
    ctx = ContextWrapper.user(new_player.id)
    await disp.MATCH_DM_PING.send(ctx)


def switch_turn(process, team):
    """
    Change the team who can pick.

    :param process: Process object calling this function
    :param team: The team who is currently picking
    :return: Next team to pick
    """
    # Toggle turn
    team.captain.is_turn = False

    # Get the other team
    other = process.match.teams[team.id - 1]
    other.captain.is_turn = True
    process.picking_captain = other.captain
    return other


async def after_pick_sub(match, subbed, force_player, clean_subbed=True):
    """
    Substitute a player by another one picked at random in the lobby.

    :param clean_subbed: Specify if subbed player should be cleaned
    :param ctx: Context used for displaying messages
    :param match: Match calling this function
    :param subbed: Player player to be subbed
    :return: Nothing
    """
    # Get a new player for substitution
    if force_player:
        new_player = force_player
    else:
        new_player = await get_substitute(match, subbed)
        if not new_player:
            return

    # Get active version of the player and clean the player object
    a_sub = subbed.active
    if clean_subbed:
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

    return new_player


class SubHandler:
    def __init__(self, match, custom_sub=None):
        self.match = match
        self.validator = CaptainValidator(match.teams[0].captain, match.teams[1].captain, match.channel)
        self.sub_func = custom_sub

        @self.validator.confirm()
        async def do_sub(ctx, captain, subbed, force_player=None):
            if self.sub_func:
                await self.sub_func(subbed, force_player)
            else:
                await after_pick_sub(self.match, subbed, force_player)

    async def sub_request(self, ctx, captain, args):
        if await self.validator.check_message(ctx, captain, args):
            return

        subbed = None
        if len(ctx.message.mentions) > 0:
            subbed = Player.get(ctx.message.mentions[0].id)
            if not subbed:
                await disp.RM_NOT_IN_DB.send(ctx)
                return
            if not(subbed.match and subbed.match.id == self.match.id):
                await disp.SUB_NO.send(ctx)
                return
        else:
            await disp.RM_MENTION_ONE.send(ctx)
            return

        if roles.is_admin(ctx.author):
            player = None
            if len(ctx.message.mentions) > 1:
                player = Player.get(ctx.message.mentions[1].id)
                if not player:
                    await disp.RM_NOT_IN_DB.send(ctx)
                    return
                elif player.match:
                    await disp.SUB_NO.send(ctx)
                    return
            await self.validator.force_confirm(ctx, captain, subbed=subbed, force_player=player)
            return
        else:
            if len(ctx.message.mentions) > 1:
                await disp.RM_MENTION_ONE.send(ctx)
                return

        other_captain = self.match.teams[captain.team.id - 1].captain
        msg = await disp.SUB_OK_CONFIRM.send(self.match.channel, subbed.mention, other_captain.mention)
        await self.validator.wait_valid(captain, msg, subbed=subbed)

    async def clean(self):
        await self.validator.clean()


async def check_faction(ctx, args):
    """
    Check if args contain a valid faction, if not display an error message

    :param ctx: Context used for displaying messages
    :param args: args to be examined
    :return: Message that was sent (None if no error message)
    """
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
    """
    Change team faction to requested one

    :param ctx: Context used for displaying messages
    :param captain: Captain asking for the faction change
    :param args: args sent by the captain
    :param match: Match calling this function
    :return: Nothing
    """
    # Check if faction is valid
    if await check_faction(ctx, args):
        # If error, return
        return

    # Get selected faction, get teams
    faction = cfg.i_factions[args[0].upper()]
    team = captain.team
    other = match.teams[team.id - 1]

    # Check if faction is already used, update faction
    if team.faction == faction:
        await disp.PK_FACTION_ALREADY.send(ctx, cfg.factions[faction])
    elif other.faction == faction:
        await disp.PK_FACTION_OTHER.send(ctx)
    else:
        team.faction = faction
        await disp.PK_FACTION_CHANGED.send(ctx, team.name, cfg.factions[faction])
