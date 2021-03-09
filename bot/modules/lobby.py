import modules.config as cfg
from display.strings import AllStrings as display
from display.classes import ContextWrapper

from random import choice as random_choice
from lib.tasks import Loop, loop
from logging import getLogger

log = getLogger("pog_bot")

_lobby_list = list()
_lobby_stuck = False
MatchClass = None

def init(m_cls):
    global MatchClass
    MatchClass = m_cls

def is_lobby_stuck():
    return _lobby_stuck

def set_lobby_stuck(bl):
    global _lobby_stuck
    _lobby_stuck = bl


def _auto_ping_threshold():
    thresh = cfg.general["lobby_size"] - cfg.general["lobby_size"] // 3
    return thresh

def _auto_ping_cancel():
    _auto_ping.cancel()
    _auto_ping.already = False

def get_sub():
    if len(_lobby_list) == 0:
        return
    player = random_choice(_lobby_list)
    _lobby_list.remove(player)
    _on_lobby_remove()
    return player


def add_to_lobby(player):
    _lobby_list.append(player)
    player.on_lobby_add()
    if len(_lobby_list) == cfg.general["lobby_size"]:
        _start_match_from_full_lobby()
    elif len(_lobby_list) >= _auto_ping_threshold():
        if not _auto_ping.is_running() and not _auto_ping.already:
            _auto_ping.start()
            _auto_ping.already = True


@loop(minutes=3, delay=1, count=2)
async def _auto_ping():
    if MatchClass.find_empty() is None:
        return
    await display.LB_NOTIFY.send(ContextWrapper.channel(cfg.channels["lobby"]), f'<@&{cfg.roles["notify"]}>')
_auto_ping.already = False


def get_lobby_len():
    return len(_lobby_list)


def get_all_names_in_lobby():
    names = [p.mention for p in _lobby_list]
    return names


def get_all_ids_in_lobby():
    ids = [str(p.id) for p in _lobby_list]
    return ids


def remove_from_lobby(player):
    _lobby_list.remove(player)
    _on_lobby_remove()
    player.on_lobby_leave()


def _on_match_free():
    _auto_ping.already = True
    if len(_lobby_list) == cfg.general["lobby_size"]:
        _start_match_from_full_lobby()


def _on_lobby_remove():
    set_lobby_stuck(False)
    if len(_lobby_list) < _auto_ping_threshold():
        _auto_ping_cancel()

def _start_match_from_full_lobby():
    match = MatchClass.find_empty()
    _auto_ping_cancel()
    if match is None:
        set_lobby_stuck(True)
        Loop(coro=_start_match_display, count=1).start(match)
    else:
        set_lobby_stuck(False)
        match.spin_up(_lobby_list)
        _lobby_list.clear()
        Loop(coro=_start_match_display, count=1).start(match)

async def _start_match_display(match):
    if not match:
        await display.LB_STUCK.send(ContextWrapper.channel(cfg.channels["lobby"]))
    else:
        await display.LB_MATCH_STARTING.send(ContextWrapper.channel(cfg.channels["lobby"]), match.channel.id)

async def on_inactive_confirmed(player):
    remove_from_lobby(player)
    await display.LB_WENT_INACTIVE.send(ContextWrapper.channel(cfg.channels["lobby"]), player.mention, names_in_lobby=get_all_names_in_lobby())


def clear_lobby():
    if len(_lobby_list) == 0:
        return False
    for p in _lobby_list:
        p.on_lobby_leave()
    _lobby_list.clear()
    _on_lobby_remove()
    return True
