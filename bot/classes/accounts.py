# @CHECK 2.0 features OK

""" This class handles the account tracking and distribution.
    Account sheet is retrieved at bot init, and then all operations are done in memory.
    Account sheet is updated at the end of each match.
    This way, if players don't accept their accounts or if a match is canceled, account info is not tracked in the sheet.
    If the accounts in memory and on account sheet are ever different, account tracking and distribution will break.
    Therefore the account sheet should be read only for humans on google drive.
"""

# Ext imports
from gspread import service_account
from gspread.exceptions import APIError
from numpy import array, vstack
from datetime import datetime as dt
from discord.errors import Forbidden
from asyncio import get_event_loop
from logging import getLogger

from lib.tasks import loop

# Custom modules
import modules.config as cfg
from display import channel_send, private_send, edit
from modules.exceptions import AccountsNotEnough
from modules.reactions import ReactionHandler, add_handler, rem_handler

X_OFFSET = 3
Y_OFFSET = 3
QUIT_DELAY = 300

log = getLogger("pog_bot")

def get_not_ready_players(team):
    not_ready = list()
    for p in team.players:
        if p.has_own_account:
            continue
        if p.account is None:
            log.error(f"Debug: {p.name} has no account")  # Should not happen
        if not p.account.is_validated:
            not_ready.append(p)
    return not_ready

class Account:
    """ Account object, each of these represent one single account"""

    def __init__(self, id, ident, pwd, x):
        self.__strId = id  # str_id to keep the 0, example: PSBx0123 would be 0123
        self.__id = int(id)  # actual id
        self.__ident = ident  # ps2 account username
        self.__pwd = pwd  # ps2 account password
        self.__x = x  # x coordinate of the account in the account sheet
        self.__aPlayer = None  # player who received the account
        self.message = None  # Message when giving the account
        self.__isValidated = False  # Has player accepted the account?
        self.is_destroyed = False  # flag account to be destroyed (removing account info from the message)

    @property
    def ident(self):
        return self.__ident

    @property
    def pwd(self):
        return self.__pwd

    @property
    def id(self):
        return self.__id

    @property
    def str_id(self):
        return self.__strId

    @property
    def x(self):
        return self.__x

    @property
    def a_player(self):
        return self.__aPlayer

    @a_player.setter
    def a_player(self, ap):
        ap.account = self
        self.__aPlayer = ap

    @property
    def is_validated(self):
        return self.__isValidated

    def validate(self):
        self.__isValidated = True
        self.__aPlayer.accept_account()


class AccountHander:
    """ AccountHander object, interface for giving accounts"""

    _currentNumber = 0  # number of matches played/registered in the sheet
    _sheetTab = None  # numpy array of the account sheet, in memory for internal work, only pushed to sheets at the end of the matches
    _secretFile = ""  # gspread ident file

    @classmethod
    def init(cls, secret_file):  # global init: retrieving data once, will work in memory afterwards
        cls._secretFile = secret_file
        gc = service_account(filename=secret_file)
        sh = gc.open_by_key(cfg.database["accounts"])
        raw_sheet = sh.worksheet("RAW")
        cls._sheetTab = array(raw_sheet.get_all_values())
        cls._currentNumber = int(cls._sheetTab[-1][0])

    def __init__(self, match):
        self.__freeAccounts = list()
        self.__yCoord = 0
        self.__xMax = 0
        self.__match = match
        type(self)._currentNumber += 1
        self.__handingStamp = 0  # timestamp: when have these accounts been given?
        match.number = type(self)._currentNumber
        self.__reactionHandler = ReactionHandler(rem_user_react=False, rem_bot_react=True)
        self.__reactionHandler.set_reaction('✅', on_account_reaction)

    def __letterFromNumber(self, num):
        """ Utility method to convert number in sheet coordinate
            For example 0=A, 25=Z, 26=AA, 27=AB, etc."""
        lets = ""
        if num >= 26:
            lets += chr(ord('@') + num // 26)
        lets += chr(ord('@') + num % 26 + 1)
        return lets

    def __getAccounts(self, stamp):
        """ Get all available accounts at a given time"""
        sheet_tab = type(self)._sheetTab
        num_matches = sheet_tab.shape[0] - Y_OFFSET
        num_accounts = sheet_tab.shape[1] - X_OFFSET

        self.__freeAccounts.clear()

        # Get all accounts
        for i in range(num_accounts):
            free = True  # free by default
            for j in range(num_matches):
                end_stamp = sheet_tab[-j - 1][2]
                if end_stamp == "" or int(end_stamp) > stamp:  # Check for all matches still happening
                    if sheet_tab[-j - 1][i + X_OFFSET] != "":  # if someone have this account
                        free = False  # it is not free
                        break
            if free:
                args = sheet_tab[0][i + X_OFFSET], sheet_tab[1][i + X_OFFSET], sheet_tab[2][i + X_OFFSET], i + X_OFFSET
                self.__freeAccounts.append(Account(*args))  # if free, add an account object to the list

        self.__yCoord = num_matches + Y_OFFSET + 1  # coordinate for this match
        self.__xMax = sheet_tab.shape[1]

    async def do_update(self):
        """ launch the update function asynchronously"""
        if len(self.__freeAccounts) == 0:
            return
        row = [''] * self.__xMax
        v_row = [''] * self.__xMax
        row[0] = str(self.__match.number)
        v_row[0] = f"Match {row[0]}"
        row[1] = str(self.__handingStamp)
        if self.__handingStamp == 0:
            v_row[1] = "ERROR in match!"
        else:
            v_row[1] = dt.utcfromtimestamp(self.__handingStamp).strftime("%Y-%m-%d %H:%M UTC")
        closing_stamp = int(dt.timestamp(dt.now())) + QUIT_DELAY
        type(self)._sheetTab[self.__yCoord - 1][2] = str(closing_stamp)
        row[2] = str(closing_stamp)
        v_row[2] = dt.utcfromtimestamp(closing_stamp).strftime("%Y-%m-%d %H:%M UTC")
        for acc in self.__freeAccounts:
            if acc.is_validated:
                row[acc.x] = str(acc.a_player.id)
                v_row[acc.x] = acc.a_player.name
        self._updateSheet.start(row, v_row)
        for acc in self.__freeAccounts:
            if acc.message is not None:
                rem_handler(acc.message.id)
                acc.is_destroyed = True
                await edit("ACC_UPDATE", acc.message, account=acc)
                if acc.is_validated:
                    await private_send("ACC_OVER", acc.a_player.id)
                else:
                    await self.__reactionHandler.auto_remove_reactions(acc.message)

    @loop(seconds=2, count=5)
    async def _updateSheet(self, row, v_row):
        """ Push updates to the google sheet"""
        loop = get_event_loop()
        log.info(f"GSpread loop on match: {self.__match.number}")
        try:
            await loop.run_in_executor(None, self.__pushUpdateToSheet, row, v_row)
        except APIError as e:
            log.warning(f"GSpread APIError on match: {self.__match.number}\n{e}")
            return
        log.info(f"GSpread ok on match: {self.__match.number}")
        self._updateSheet.cancel()

    def __pushUpdateToSheet(self, row, v_row):
        gc = service_account(filename=type(self)._secretFile)
        sh = gc.open_by_key(cfg.database["accounts"])
        raw_sheet = sh.worksheet("RAW")
        visible_sheet = sh.worksheet("VISIBLE")
        lt = self.__letterFromNumber(self.__xMax - 1)
        y = self.__yCoord
        raw_sheet.update(f"A{y}:{lt}{y}", [row])
        visible_sheet.update(f"A{y}:{lt}{y}", [v_row])

    async def give_accounts(self):
        """ Find available accounts for all players registered without an account"""
        await channel_send("ACC_SENDING", self.__match.id)
        p_list = list()
        for tm in self.__match.teams:
            for a_player in tm.players:
                p_list.append(a_player)

        stamp = int(dt.timestamp(dt.now()))
        self.__getAccounts(stamp)

        new_line = [""] * self.__xMax

        new_line[0] = str(self.__match.number)
        new_line[1] = str(stamp)
        i = 0
        for a_player in p_list:
            if not a_player.has_own_account:
                if i == len(self.__freeAccounts):
                    raise AccountsNotEnough  # not enough accounts for all the player without account
                current_acc = self.__freeAccounts[i]
                current_acc.a_player = a_player
                new_line[current_acc.x] = str(a_player.id)
                try:
                    msg = await private_send("ACC_UPDATE", a_player.id, account=current_acc)
                    add_handler(msg.id, self.__reactionHandler)
                    await self.__reactionHandler.auto_add_reactions(msg)
                except Forbidden:
                    msg = await channel_send("ACC_CLOSED", self.__match.id, a_player.mention)
                current_acc.message = msg
                i += 1
        type(self)._sheetTab = vstack((type(self)._sheetTab, array(new_line)))
        self.__handingStamp = stamp
        await channel_send("ACC_SENT", self.__match.id)


async def on_account_reaction(reaction, player):
    account = player.active.account
    account.validate()
    await edit("ACC_UPDATE", account.message, account=account)
