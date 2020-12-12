import modules.config as cfg
from modules.exceptions import UnexpectedError, AccountsNotEnough, \
    ElementNotFound, UserLackingPermission, AlreadyPicked
from display import SendCtx, send
from modules.enumerations import PlayerStatus, MatchStatus, SelStatus
from modules.image_maker import publish_match_image
from modules.census import process_score, get_offline_players
from modules.database import update_match
from datetime import datetime as dt, timezone as tz
from modules.ts_interface import AudioBot
from modules.reactions import ReactionHandler, add_handler

from classes.teams import Team  # ok
from classes.players import TeamCaptain, ActivePlayer  # ok
from classes.maps import MapSelection, main_maps_pool  # ok
from classes.accounts import AccountHander  # ok

from random import choice as random_choice
from lib.tasks import loop
from asyncio import sleep
from logging import getLogger

log = getLogger("pog_bot")

_lobby_list = list()
_lobby_stuck = False

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

def _get_sub():
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
        start_match_from_full_lobby.start()
    elif len(_lobby_list) >= _auto_ping_threshold():
        if not _auto_ping.is_running() and not _auto_ping.already:
            _auto_ping.start()
            _auto_ping.already = True


@loop(minutes=3, delay=1, count=2)
async def _auto_ping():
    if _find_spot_for_match() is None:
        return
    await send("LB_NOTIFY", SendCtx.channel(cfg.channels["lobby"]), f'<@&{cfg.roles["notify"]}>')
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
        start_match_from_full_lobby.start()


def _on_lobby_remove():
    set_lobby_stuck(False)
    if len(_lobby_list) < _auto_ping_threshold():
        _auto_ping_cancel()


@loop(count=1)
async def start_match_from_full_lobby():
    match = _find_spot_for_match()
    _auto_ping_cancel()
    if match is None:
        set_lobby_stuck(True)
        await send("LB_STUCK", SendCtx.channel(cfg.channels["lobby"]))
        return
    set_lobby_stuck(False)
    match._set_player_list(_lobby_list)
    for p in _lobby_list:
        p.on_match_selected(match)
    _lobby_list.clear()
    match._launch.start()
    await send("LB_MATCH_STARTING", SendCtx.channel(cfg.channels["lobby"]), match.id)

async def on_inactive_confirmed(player):
    remove_from_lobby(player)
    await send("LB_WENT_INACTIVE", SendCtx.channel(cfg.channels["lobby"]), player.mention, names_in_lobby=get_all_names_in_lobby())


def clear_lobby():
    if len(_lobby_list) == 0:
        return False
    for p in _lobby_list:
        p.on_lobby_leave()
    _lobby_list.clear()
    _on_lobby_remove()
    return True


def _find_spot_for_match():
    for match in _all_matches.values():
        if match.status is MatchStatus.IS_FREE:
            return match
    return None