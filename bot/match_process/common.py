
from display import send, SendCtx
from modules.lobby import get_sub, get_all_names_in_lobby
import modules.config as cfg
from lib.tasks import Loop
from asyncio import sleep

async def get_substitute(match):
    # Get a new player from the lobby, if None available, display
    new_player = get_sub()
    if new_player is None:
        await send("SUB_NO_PLAYER", match.channel)
        return

    # We have a player. Ping them in the lobby and change their status
    Loop(coro=ping_sub_in_lobby, count=1).start(match, new_player)

    new_player.on_match_selected(match.proxy)
    return new_player

async def ping_sub_in_lobby(match, new_player):
    await send("SUB_LOBBY", SendCtx.channel(cfg.channels["lobby"]),\
                            new_player.mention, match.channel.id,\
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