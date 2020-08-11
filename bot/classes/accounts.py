""" Handle the accounts
    Account sheet is retreived at init, and then all operations are done in memory
    Account sheet is updated at the end of each match
    Like so, when players didn't accept their accounts or when match got canceled, players who didn't see the accounts info are not tracked in the sheet
    The day memory and account sheet gets different, everything is broken. Account sheet should be read only for humans on google drive
"""

# Ext imports
from gspread import service_account
from numpy import array, vstack
from datetime import datetime as dt
from lib import tasks
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor

# Custom modules
import modules.config as cfg
from modules.display import channelSend, privateSend, edit, remReaction
from modules.exceptions import AccountsNotEnough

X_OFFSET=3
Y_OFFSET=3
QUIT_DELAY = 300


class Account():
    """ Account object, each of these represent one single account
    """
    def __init__(self, id, ident, pwd, x):
        self.__strId = id       # strId to keep the 0, example: PSBx0123 would be 0123
        self.__id = int(id)     # actual id
        self.__ident = ident    # ps2 account username
        self.__pwd = pwd        # ps2 account password
        self.__x = x            # x coordiante of the account in the account sheet
        self.__aPlayer = None   # player who received the account
        self.message = None     # Message when giving the account
        self.__isValidated = False  # Has player accepted the account?
        self.isDestroyed = False    # flag account to be destroyed (removing account info from the message)

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
    def strId(self):
        return self.__strId

    @property
    def x(self):
        return self.__x

    @property
    def aPlayer(self):
        return self.__aPlayer

    @aPlayer.setter
    def aPlayer(self, ap):
        ap.account = self
        self.__aPlayer = ap

    @property
    def isValidated(self):
        return self.__isValidated

    def validate(self):
        self.__isValidated = True
        self.__aPlayer.acceptAccount()



class AccountHander():
    """ AccountHander object, interface for giving accounts
    """

    _currentNumber = 0  # number of matches played/registered in the sheet
    _sheetTab = None    # numpy array of the account sheet, in memory for internal work, only pushed to sheets at the end of the matches
    _secretFile = ""    # gspread ident file

    @classmethod
    def init(cls, secretFile): # global init: retrieving data once, will work in memory afterwards
        cls._secretFile = secretFile
        gc = service_account(filename=secretFile)
        sh = gc.open_by_key(cfg.database["accounts"])
        rawSheet = sh.worksheet("RAW")
        cls._sheetTab = array(rawSheet.get_all_values())
        cls._currentNumber = int(cls._sheetTab[-1][0])

    def __init__(self, match):
        self.__freeAccounts = list()
        self.__yCoord = 0
        self.__xMax = 0
        self.__match = match
        type(self)._currentNumber+=1
        self.__handingStamp = 0     # timestamp: when have these accounts been given?
        match.number = type(self)._currentNumber

    def __letterFromNumber(self, num):
        """ Utility method to convert number in sheet coordinate
            For example 0=A, 25=Z, 26=AA, 27=AB, etc
        """
        lets=""
        if num>=26:
            lets += chr(ord('@')+num//26)
        lets+=chr(ord('@')+num%26+1)
        return lets

    def __getAccounts(self, stamp):
        """ Get all free accounts at a given time
        """
        sheetTab = type(self)._sheetTab
        numMatches = sheetTab.shape[0]-Y_OFFSET
        numAccounts = sheetTab.shape[1]-X_OFFSET

        self.__freeAccounts.clear()

        # Get all accounts
        for i in range(numAccounts):
            free = True # free by default
            for j in range(numMatches):
                endStamp = sheetTab[-j-1][2]
                if endStamp == "" or int(endStamp) > stamp: # Check for all matches still happening
                    if sheetTab[-j-1][i+X_OFFSET] != "": # if someone have this account
                        free = False # it is not free
                        break
            if free:
                args = sheetTab[0][i+X_OFFSET], sheetTab[1][i+X_OFFSET], sheetTab[2][i+X_OFFSET], i+X_OFFSET
                self.__freeAccounts.append(Account(*args)) # if free, add an account object to the list

        self.__yCoord = numMatches+Y_OFFSET+1 # coordinate for this match
        self.__xMax = sheetTab.shape[1]

    async def doUpdate(self):
        """ launch the update function asynchronously
        """
        if len(self.__freeAccounts) == 0:
            return
        loop = get_event_loop()
        await loop.run_in_executor(ThreadPoolExecutor(), self.__updateSheet)
        for acc in self.__freeAccounts:
            if acc.message != None:
                acc.isDestroyed = True
                await edit("ACC_UPDATE", acc.message, account=acc)
                if acc.isValidated:
                    await privateSend("ACC_OVER", acc.aPlayer.id)
                else:
                    await remReaction(acc.message)


    def __updateSheet(self):
        """ Push updates to the google sheet
        """
        gc = service_account(filename=type(self)._secretFile)
        sh = gc.open_by_key(cfg.database["accounts"])
        rawSheet = sh.worksheet("RAW")
        visibleSheet = sh.worksheet("VISIBLE")
        # row will be raw data while vrow will be user-readable data
        row = ['']*self.__xMax
        vRow = ['']*self.__xMax
        row[0] = str(self.__match.number)
        vRow[0] = f"Match {row[0]}"
        row[1] = str(self.__handingStamp)
        if self.__handingStamp == 0:
            vRow[1] = "ERROR in match!"
        else:
            vRow[1] = dt.utcfromtimestamp(self.__handingStamp).strftime("%Y-%m-%d %H:%M UTC")
        closingStamp =  int(dt.timestamp(dt.now())) + QUIT_DELAY
        type(self)._sheetTab[self.__yCoord-1][2] = str(closingStamp)
        row[2] = str(closingStamp)
        vRow[2] = dt.utcfromtimestamp(closingStamp).strftime("%Y-%m-%d %H:%M UTC")
        for acc in self.__freeAccounts:
            if acc.isValidated:
                row[acc.x] = str(acc.aPlayer.id)
                vRow[acc.x] = acc.aPlayer.name
        lt = self.__letterFromNumber(self.__xMax-1)
        y = self.__yCoord
        rawSheet.update(f"A{y}:{lt}{y}", [row])
        visibleSheet.update(f"A{y}:{lt}{y}", [vRow])


    async def give_accounts(self):
        """ Find free accounts for all players needing some
        """
        await channelSend("ACC_SENDING", self.__match.id)
        pList = list()
        for tm in self.__match.teams:
            for aPlayer in tm.players:
                pList.append(aPlayer)

        stamp = int(dt.timestamp(dt.now()))
        self.__getAccounts(stamp)

        newLine = [""]*self.__xMax

        newLine[0] = str(self.__match.number)
        newLine[1] = str(stamp)
        i = 0
        for aPlayer in pList:
            if not aPlayer.hasOwnAccount:
                if i == len(self.__freeAccounts):
                    raise AccountsNotEnough # not enough accounts for all the player without account
                currentAcc = self.__freeAccounts[i]
                currentAcc.aPlayer = aPlayer
                newLine[currentAcc.x] = str(aPlayer.id)
                msg = await privateSend("ACC_UPDATE", aPlayer.id, account=currentAcc)
                await msg.add_reaction('✅')
                currentAcc.message = msg
                i+=1
        type(self)._sheetTab = vstack((type(self)._sheetTab, array(newLine)))
        self.__handingStamp = stamp
        await channelSend("ACC_SENT", self.__match.id)



