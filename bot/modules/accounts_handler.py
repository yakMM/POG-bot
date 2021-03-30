import modules.config as cfg

from logging import getLogger
from gspread import service_account
from gspread.exceptions import APIError
from numpy import array, vstack
from modules.tools import UnexpectedError
from display import AllStrings as disp, ContextWrapper

from datetime import datetime as dt

import discord.errors

import modules.database as db
import modules.reactions as reactions

import classes

log = getLogger("pog_bot")

_busy_accounts = dict()
_available_accounts = dict()
_reaction_handler = reactions.ReactionHandler(rem_user_react=False, rem_bot_react=True)

X_OFFSET = 1
Y_OFFSET = 2


@_reaction_handler.reaction('✅')
async def on_account_reaction(reaction, player, user, msg):
    account = player.active.account
    await account.validate()
    await disp.ACC_UPDATE.edit(account.message, account=account)


def init(secret_file):
    gc = service_account(filename=secret_file)
    sh = gc.open_by_key(cfg.database["accounts"])
    raw_sheet = sh.worksheet("1")
    sheet_tab = array(raw_sheet.get_all_values())

    num_accounts = sheet_tab.shape[0] - Y_OFFSET

    # Get all accounts
    for i in range(num_accounts):
        a_id_str = sheet_tab[i + Y_OFFSET][X_OFFSET]
        a_username = sheet_tab[i + Y_OFFSET][X_OFFSET + 1]
        a_password = sheet_tab[i + Y_OFFSET][X_OFFSET + 2]
        a_id = int(a_id_str)

        if a_id in _available_accounts:
            _available_accounts[a_id].update(a_username, a_password)
        elif a_id in _busy_accounts:
            _busy_accounts[a_id].update(a_username, a_password)
        else:
            unique_usages = db.get_field("accounts_usage", a_id, "unique_usages")
            if unique_usages is None:
                raise UnexpectedError(f"Can't find usage for account {a_id}")
            _available_accounts[a_id] = classes.Account(a_id_str, a_username, a_password, unique_usages)


async def give_account(a_player):
    unique_usages = await db.async_db_call(db.get_field, "accounts_usage", a_player.id, "unique_usages")
    if not unique_usages:
        unique_usages = list()

    a_player.unique_usages = unique_usages

    if len(_available_accounts) == 0:
        return False

    potential = list()
    for acc_id in unique_usages:
        if acc_id in _available_accounts:
            potential.append(_available_accounts[acc_id])

    if potential:
        max_obj = potential[0]
        max_value = max_obj.nb_unique_usages
        for acc in potential:
            n_usages = acc.nb_unique_usages
            if n_usages > max_value:
                max_obj = acc
                max_value = n_usages
        _set_account(max_obj, a_player)
        return True

    min_obj = list(_available_accounts.values())[0]
    min_value = min_obj.nb_unique_usages
    for acc in _available_accounts.values():
        n_usages = acc.nb_unique_usages
        if n_usages < min_value:
            min_obj = acc
            min_value = n_usages
    _set_account(min_obj, a_player)
    return True


def _set_account(acc, a_player):
    print(f"give {acc.id} to {a_player.name}")
    del _available_accounts[acc.id]
    _busy_accounts[acc.id] = acc
    acc.a_player = a_player
    acc.add_usage(a_player.id, a_player.match.id)
    a_player.account = acc


async def send_account(channel, a_player):
    msg = None
    for j in range(3):
        try:
            msg = await disp.ACC_UPDATE.send(ContextWrapper.user(a_player.id), account=a_player.account)
            break
        except discord.errors.Forbidden:
            pass
    if msg:
        reactions.add_handler(msg.id, _reaction_handler)
        await _reaction_handler.auto_add_reactions(msg)
        a_player.account.message = msg
    else:
        await disp.ACC_CLOSED.send(channel, a_player.mention)
        await a_player.account.validate()
        msg = await disp.ACC_STAFF.send(ContextWrapper.channel(cfg.channels["staff"]),
                                        f'<@&{cfg.roles["admin"]}>', a_player.mention, account=a_player.account)
        a_player.account.message = msg


async def terminate_account(a_player):
    acc = a_player.account
    acc.terminate()
    reactions.rem_handler(acc.message.id)
    await disp.ACC_UPDATE.edit(acc.message, account=acc)
    if acc.is_validated and acc.message.channel.id != cfg.channels["staff"]:
        await disp.ACC_OVER.send(ContextWrapper.user(acc.a_player.id))
    else:
        await _reaction_handler.auto_remove_reactions(acc.message)

    if acc.is_validated:
        # Update db
        p_usage = dict()
        p_usage["id"] = acc.id
        p_usage["time_start"] = acc.last_usage["time_start"]
        p_usage["time_stop"] = acc.last_usage["time_stop"]
        p_usage["match_id"] = a_player.match.id
        # Account entry
        await db.async_db_call(db.push_element, "accounts_usage", acc.id, {"usages": acc.last_usage})
        try:
            # Player entry
            await db.async_db_call(db.push_element, "accounts_usage", a_player.id, {"usages": p_usage})
        except db.DatabaseError:
            data = dict()
            data["_id"] = a_player.id
            data["unique_usages"] = a_player.unique_usages
            data["usages"] = [p_usage]
            await db.async_db_call(db.set_element, "accounts_usage", a_player.id, data)

    acc.clean()
    del _busy_accounts[acc.id]
    _available_accounts[acc.id] = acc


def get_not_validated_accounts(team):
    not_ready = list()
    for p in team.players:
        if p.has_own_account:
            continue
        if p.account is None:
            log.error(f"Debug: {p.name} has no account")  # Should not happen
        if not p.account.is_validated:
            not_ready.append(p)
    return not_ready

