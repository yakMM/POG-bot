# @CHECK 2.0 features OK

""" This class handles the account tracking and distribution.
    Account sheet is retrieved at bot init, and then all operations are done in memory.
    Account sheet is updated at the end of each match.
    This way, if players don't accept their accounts or if a match is canceled, account info is not tracked in the sheet.
    If the accounts in memory and on account sheet are ever different, account tracking and distribution will break.
    Therefore the account sheet should be read only for humans on google drive.
"""

# Ext imports
from logging import getLogger
import modules.database as db
import modules.tools as tools

QUIT_DELAY = 300

log = getLogger("pog_bot")

class Account:
    """ Account object, each of these represent one single account"""

    def __init__(self, a_id, username, password, unique_usages):
        self.__str_id = a_id  # str_id to keep the 0, example: PSBx0123 would be 0123
        self.__id = int(a_id)  # actual id
        self.__username = username  # ps2 account username
        self.__password = password  # ps2 account password
        self.a_player = None  # player who received the account
        self.message = None  # Message when giving the account
        self.__is_validated = False  # Has player accepted the account?
        self.__is_destroyed = False  # flag account to be destroyed (removing account info from the message)
        self.__last_usage = None
        self.__unique_usages = unique_usages

    def update(self, username, password):
        self.__username = username
        self.__password = password

    @property
    def is_destroyed(self):
        return self.__is_destroyed

    @property
    def nb_unique_usages(self):
        return len(self.__unique_usages)

    @property
    def unique_usages(self):
        return self.__unique_usages

    @property
    def username(self):
        return self.__username

    @property
    def password(self):
        return self.__password

    @property
    def id(self):
        return self.__id

    @property
    def str_id(self):
        return self.__str_id

    @property
    def is_validated(self):
        return self.__is_validated

    @property
    def last_usage(self):
        return self.__last_usage

    def clean(self):
        self.__is_validated = False
        self.__is_destroyed = False
        self.a_player = None
        self.message = None
        self.__last_usage = None

    def add_usage(self, p_id, m_number):
        self.__last_usage = {"id": p_id, "match_id": m_number}

    async def validate(self):
        self.__is_validated = True
        await self.a_player.accept_account()
        self.__last_usage["time_start"] = tools.timestamp_now()
        if self.a_player.id not in self.__unique_usages:
            self.__unique_usages.append(self.a_player.id)
            await db.async_db_call(db.push_element, "accounts_usage", self.__id,
                                                    {"unique_usages": self.a_player.id})

    def terminate(self):
        self.__last_usage["time_stop"] = tools.timestamp_now()
        self.__is_destroyed = True
