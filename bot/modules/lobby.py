import modules.config as cfg
from display import AllStrings as disp, ContextWrapper, views, InteractionContext

from lib.tasks import Loop, loop
from logging import getLogger

import modules.tools as tools
import modules.interactions as interactions

log = getLogger("pog_bot")

_lobby_list = list()
_lobby_stuck = False
_MatchClass = None
_client = None
_warned_players = dict()


def reset_timeout(player):
    _remove_from_warned(player)
    player.reset_lobby_expiration()


def init(m_cls, client):
    global _MatchClass
    global _client
    _MatchClass = m_cls
    _client = client
    _lobby_loop.start()


def _remove_from_warned(p):
    if p in _warned_players:
        _warned_players[p].clean()
        del _warned_players[p]


def _clear_warned():
    for k in list(_warned_players.values()):
        k.clean()
    _warned_players.clear()


def _add_ih_callback(ih, player):
    @ih.callback('reset')
    async def on_user_react(p, interaction_id, interaction, interaction_values):
        user = interaction.user
        if user.id == player.id:
            ctx = ContextWrapper.channel(cfg.channels["lobby"])
            ctx.author = user
            reset_timeout(player)
            await disp.LB_REFRESHED.send(ctx, names_in_lobby=get_all_names_in_lobby())
        else:
            i_ctx = InteractionContext(interaction)
            await disp.LB_REFRESH_NO.send(i_ctx)
            raise interactions.InteractionNotAllowed


def is_lobby_stuck():
    return _lobby_stuck


def _set_lobby_stuck(bl):
    global _lobby_stuck
    _lobby_stuck = bl


@loop(minutes=1)
async def _lobby_loop():
    for p in _lobby_list:
        if p.is_lobby_expired:
            remove_from_lobby(p)
            await disp.LB_TOO_LONG.send(ContextWrapper.channel(cfg.channels["lobby"]),
                                        p.mention,
                                        names_in_lobby=get_all_names_in_lobby())
        elif p.should_be_warned and p not in _warned_players:
            ih = interactions.InteractionHandler(p, views.reset_button)
            _warned_players[p] = ih
            _add_ih_callback(ih, p)
            ctx = ih.get_new_context(ContextWrapper.channel(cfg.channels["lobby"]))
            await disp.LB_WARNING.send(ctx, p.mention)


def _auto_ping_threshold():
    thresh = cfg.general["lobby_size"] - cfg.general["lobby_size"] // 3
    return thresh


def _auto_ping_cancel():
    _auto_ping.cancel()
    _auto_ping.already = False


def get_sub(player):
    # Check if someone in lobby, if not return player (might be None)
    if len(_lobby_list) == 0:
        return player
    # If player is None, take first player in queue
    if not player:
        player = _lobby_list[0]
    # If player chosen is in lobby, remove
    if player.is_lobbied:
        _lobby_list.remove(player)
        _on_lobby_remove()
        _remove_from_warned(player)
    return player


def add_to_lobby(player, expiration=0):
    _lobby_list.append(player)
    player.on_lobby_add(expiration)
    all_names = get_all_names_in_lobby()
    if len(_lobby_list) == cfg.general["lobby_size"]:
        _start_match_from_full_lobby()
    elif len(_lobby_list) >= _auto_ping_threshold():
        if not _auto_ping.is_running() and not _auto_ping.already:
            _auto_ping.start()
            _auto_ping.already = True
    return all_names


@loop(minutes=3, delay=1, count=2)
async def _auto_ping():
    if _MatchClass.find_empty() is None:
        return
    await disp.LB_NOTIFY.send(ContextWrapper.channel(cfg.channels["lobby"]), f'<@&{cfg.roles["notify"]}>',
                              get_lobby_len(), cfg.general["lobby_size"])


_auto_ping.already = False


def get_lobby_len():
    return len(_lobby_list)


def get_all_names_in_lobby():
    names = [f"{p.mention} ({p.name}) (auto leave in {p.lobby_remaining})" for p in _lobby_list]
    return names


def get_all_ids_in_lobby():
    ids = [p.id for p in _lobby_list]
    return ids


def remove_from_lobby(player):
    _remove_from_warned(player)

    _lobby_list.remove(player)
    _on_lobby_remove()
    player.on_lobby_leave()


def on_match_free():
    _auto_ping.already = False
    if len(_lobby_list) == cfg.general["lobby_size"]:
        _start_match_from_full_lobby()


def _on_lobby_remove():
    _set_lobby_stuck(False)
    if len(_lobby_list) < _auto_ping_threshold():
        _auto_ping_cancel()


def _start_match_from_full_lobby():
    match = _MatchClass.find_empty()
    _auto_ping_cancel()
    if match is None:
        _set_lobby_stuck(True)
        Loop(coro=_send_stuck_msg, count=1).start()
    else:
        _set_lobby_stuck(False)
        match.spin_up(_lobby_list.copy())
        _lobby_list.clear()
        _clear_warned()


async def _send_stuck_msg():
    await disp.LB_STUCK.send(ContextWrapper.channel(cfg.channels["lobby"]))


def clear_lobby():
    if len(_lobby_list) == 0:
        return False
    for p in _lobby_list:
        p.on_lobby_leave()
    _lobby_list.clear()
    _clear_warned()
    _on_lobby_remove()
    return True
