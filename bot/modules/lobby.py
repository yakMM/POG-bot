import modules.config as cfg
from display.strings import AllStrings as disp
from display.classes import ContextWrapper

from random import choice as random_choice
from lib.tasks import Loop, loop
from logging import getLogger

from datetime import datetime as dt
import modules.tools as tools

log = getLogger("pog_bot")

_lobby_list = list()
_lobby_stuck = False
_MatchClass = None
_client = None
_warned_players = list()

def init(m_cls, client):
    global _MatchClass
    global _client
    _MatchClass = m_cls
    _client = client
    _lobby_loop.start()


def is_lobby_stuck():
    return _lobby_stuck

def set_lobby_stuck(bl):
    global _lobby_stuck
    _lobby_stuck = bl

# 3600, 4200
@loop(minutes=5)
async def _lobby_loop():
    for p in _lobby_list:
        now = tools.timestamp_now()
        if p.lobby_stamp < (now - 7800):
            remove_from_lobby(p)
            await disp.LB_TOO_LONG.send(ContextWrapper.channel(cfg.channels["lobby"]), p.mention,
                                        names_in_lobby=get_all_names_in_lobby())
        elif p.lobby_stamp < (now - 7200):
            if p not in _warned_players:
                await disp.LB_WARNING.send(ContextWrapper.channel(cfg.channels["lobby"]), p.mention)
                _warned_players.append(p)


def _auto_ping_threshold():
    thresh = cfg.general["lobby_size"] - cfg.general["lobby_size"] // 3
    return thresh


def _auto_ping_cancel():
    _auto_ping.cancel()
    _auto_ping.already = False


def get_sub(player):
    if len(_lobby_list) == 0:
        return player
    if not player:
        player = _lobby_list[0]
    try:
        _warned_players.remove(player)
    except ValueError:
        pass
    _lobby_list.remove(player)
    _on_lobby_remove()
    return player

def add_to_lobby(player):
    _lobby_list.append(player)
    all_names = get_all_names_in_lobby()
    player.on_lobby_add()
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
    await disp.LB_NOTIFY.send(ContextWrapper.channel(cfg.channels["lobby"]), f'<@&{cfg.roles["notify"]}>')
_auto_ping.already = False


def get_lobby_len():
    return len(_lobby_list)


def get_all_names_in_lobby():
    names = [f"{p.mention} ({p.name})" for p in _lobby_list]
    return names


def get_all_ids_in_lobby():
    ids = [p.id for p in _lobby_list]
    return ids


def remove_from_lobby(player):
    try:
        _warned_players.remove(player)
    except ValueError:
        pass
    _lobby_list.remove(player)
    _on_lobby_remove()
    player.on_lobby_leave()


def on_match_free():
    _auto_ping.already = False
    if len(_lobby_list) == cfg.general["lobby_size"]:
        _start_match_from_full_lobby()


def _on_lobby_remove():
    set_lobby_stuck(False)
    if len(_lobby_list) < _auto_ping_threshold():
        _auto_ping_cancel()

def _start_match_from_full_lobby():
    match = _MatchClass.find_empty()
    _auto_ping_cancel()
    if match is None:
        set_lobby_stuck(True)
        Loop(coro=_send_stuck_msg, count=1).start()
    else:
        set_lobby_stuck(False)
        match.spin_up(_lobby_list.copy())
        _lobby_list.clear()
        _warned_players.clear()

async def _send_stuck_msg():
    await disp.LB_STUCK.send(ContextWrapper.channel(cfg.channels["lobby"]))

def clear_lobby():
    if len(_lobby_list) == 0:
        return False
    for p in _lobby_list:
        p.on_lobby_leave()
    _lobby_list.clear()
    _warned_players.clear()
    _on_lobby_remove()
    return True
