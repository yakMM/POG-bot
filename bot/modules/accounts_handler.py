"""
| This module handle the POG Jaeger accounts.
| Initialize or reload the module with :meth:`init`.
| Then call :meth:`give_account` and :meth:`send_account` to hand an account to an in-match player.
| Use :meth:`terminate_account` to remove the account from the player.
"""

# External imports
from logging import getLogger
from gspread import service_account
from numpy import array
import discord.errors

# Internal imports
import classes
from display import AllStrings as disp, ContextWrapper, views
import modules.database as db
import modules.config as cfg
from modules.tools import UnexpectedError


log = getLogger("pog_bot")

# Will hold the Jaeger accounts
_busy_accounts = dict()
_available_accounts = dict()

# Offsets in the google sheet
X_OFFSET = 1
Y_OFFSET = 2


# Will be called at bot init or on account reload
def init(secret_file: str):
    """
    Initialize the accounts from the google sheet.
    If called later, reload the account usernames and passwords.

    :param secret_file: Name of the gspread authentication json file.
    """
    # Open the google sheet:
    gc = service_account(filename=secret_file)
    sh = gc.open_by_key(cfg.database["accounts"])
    raw_sheet = sh.worksheet("1")
    sheet_tab = array(raw_sheet.get_all_values())

    # Get total number of accounts
    num_accounts = sheet_tab.shape[0] - Y_OFFSET

    # Add accounts one by one
    for i in range(num_accounts):
        # Get account data
        a_id_str = sheet_tab[i + Y_OFFSET][X_OFFSET]
        a_username = sheet_tab[i + Y_OFFSET][X_OFFSET + 1]
        a_password = sheet_tab[i + Y_OFFSET][X_OFFSET + 2]
        a_id = int(a_id_str)

        # Update account
        if a_id in _available_accounts:
            _available_accounts[a_id].update(a_username, a_password)
        elif a_id in _busy_accounts:
            _busy_accounts[a_id].update(a_username, a_password)
        else:
            # If account doesn't exist already, initialize it
            unique_usages = db.get_field("accounts_usage", a_id, "unique_usages")
            if unique_usages is None:
                raise UnexpectedError(f"Can't find usage for account {a_id}")
            _available_accounts[a_id] = classes.Account(a_id_str, a_username, a_password, unique_usages)


async def give_account(a_player: classes.ActivePlayer) -> bool:
    """
    Give an account to a_player. We want each player to use as little accounts as possible.
    So we try to give an account the player already used.

    :param a_player: Player to give account to.
    :return: True is account given, False if not enough accounts available.
    """
    # Get player usages
    unique_usages = await db.async_db_call(db.get_field, "accounts_usage", a_player.id, "unique_usages")
    if not unique_usages:
        unique_usages = list()

    # Set player usages in the player object
    a_player.unique_usages = unique_usages

    # If no available accounts, quit
    if len(_available_accounts) == 0:
        return False

    # STEP 1.A: Check for accounts the player already used by the past
    potential = list()
    for acc_id in unique_usages:
        if acc_id in _available_accounts:
            potential.append(_available_accounts[acc_id])

    # STEP 1.B: Give the account with the biggest usages amongst the accounts found in 1.A
    if potential:
        max_obj = potential[0]
        max_value = max_obj.nb_unique_usages
        # Find max
        for acc in potential:
            n_usages = acc.nb_unique_usages
            if n_usages > max_value:
                max_obj = acc
                max_value = n_usages
        # Give account, return ok
        _set_account(max_obj, a_player)
        return True

    # STEP 2: If we couldn't find an account the player already used, give him the account with the least usages
    min_obj = list(_available_accounts.values())[0]
    min_value = min_obj.nb_unique_usages
    # Find min
    for acc in _available_accounts.values():
        n_usages = acc.nb_unique_usages
        if n_usages < min_value:
            min_obj = acc
            min_value = n_usages
    # Give account, return ok
    _set_account(min_obj, a_player)
    return True


def _set_account(acc: classes.Account, a_player: classes.ActivePlayer):
    """
    Set player's account.

    :param acc: Account to give.
    :param a_player: Player who will receive the account.
    """
    log.info(f"Give account [{acc.id}] to player: id:[{a_player.id}], name:[{a_player.name}]")

    # Put account in the busy dictionary
    del _available_accounts[acc.id]
    _busy_accounts[acc.id] = acc

    # Set account
    acc.a_player = a_player
    acc.add_usage(a_player.id, a_player.match.id)
    a_player.account = acc


async def send_account(channel: discord.TextChannel, a_player: classes.ActivePlayer):
    """
    Actually send its account to the player.

    :param channel: Current match channel.
    :param a_player: Player to send the account to.
    """
    msg = None
    # Try 3 times to send a DM:
    ctx = a_player.account.get_new_context(await ContextWrapper.user(a_player.id))
    for j in range(3):
        try:
            msg = await disp.ACC_UPDATE.send(ctx, account=a_player.account)
            break
        except discord.errors.Forbidden:
            pass
    if not msg:
        # Else validate the account and send it to staff channel instead
        await disp.ACC_CLOSED.send(channel, a_player.mention)
        await a_player.account.validate()
        msg = await disp.ACC_STAFF.send(ContextWrapper.channel(cfg.channels["staff"]),
                                        f'<@&{cfg.roles["admin"]}>', a_player.mention, account=a_player.account)
    # Set the account message, log the account:
    a_player.account.message = msg
    await disp.ACC_LOG.send(ContextWrapper.channel(cfg.channels["spam"]), a_player.name, a_player.id, a_player.account.id)


async def terminate_account(a_player: classes.ActivePlayer):
    """
    Terminate the account: ask the user to log off and remove the reaction.

    :param a_player: Player whose account should be terminated.
    """
    # Get account and terminate it
    acc = a_player.account
    acc.terminate()

    # Remove the reaction handler and update the account message
    await disp.ACC_UPDATE.edit(acc.message, account=acc)

    # If account was validated, ask the player to log off:
    if acc.is_validated and acc.message.channel.id != cfg.channels["staff"]:
        await disp.ACC_OVER.send(await ContextWrapper.user(acc.a_player.id))

    # If account was validated, update the db with usage
    if acc.is_validated:
        # Prepare data
        p_usage = {
            "id": acc.id,
            "time_start": acc.last_usage["time_start"],
            "time_stop": acc.last_usage["time_stop"],
            "match_id": a_player.match.id
        }
        # Update the account element
        await db.async_db_call(db.push_element, "accounts_usage", acc.id, {"usages": acc.last_usage})
        try:
            # Update the player element
            await db.async_db_call(db.push_element, "accounts_usage", a_player.id, {"usages": p_usage})
        except db.DatabaseError:
            # If the player element doesn't exist, create it
            data = dict()
            data["_id"] = a_player.id
            data["unique_usages"] = a_player.unique_usages
            data["usages"] = [p_usage]
            await db.async_db_call(db.set_element, "accounts_usage", a_player.id, data)

    # Reset the account state
    acc.clean()
    del _busy_accounts[acc.id]
    _available_accounts[acc.id] = acc


def get_not_validated_accounts(team: classes.Team) -> list:
    """
    Find all the accounts that were not validated within the team.

    :param team: Team to check
    :return: List containing the players who didn't accept their accounts.
    """
    not_ready = list()
    for p in team.players:
        if p.has_own_account:
            continue
        if p.is_benched:
            continue
        if p.account is None:
            log.error(f"Debug: {p.name} has no account")  # Should not happen
        if not p.account.is_validated:
            not_ready.append(p)
    return not_ready

