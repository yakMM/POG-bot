"""Contains player classes
"""
# Others

# Custom modules
import modules.config as cfg
from modules.asynchttp import request as httpRequest
from modules.exceptions import UnexpectedError, ElementNotFound, CharNotFound, CharInvalidWorld, CharMissingFaction, CharAlreadyExists, AccountNotFound, ApiNotReachable
from modules.enumerations import PlayerStatus
from lib import tasks
from modules.roles import roleUpdate
from modules.database import updatePlayer

from logging import getLogger
from datetime import datetime as dt

log = getLogger(__name__)

WORLD_ID = 19  # Jaeger ID


_allPlayers = dict()
# to store VS, NC and TR names to check for duplicates
_namesChecking = [dict(), dict(), dict()]


def getPlayer(id):
    player = _allPlayers.get(id)
    if player is None:
        raise ElementNotFound(id)
    return player


def removePlayer(p):
    if p.id not in _allPlayers:
        raise ElementNotFound(p.id)
    if p.hasOwnAccount:
        for i in range(len(_namesChecking)):
            del _namesChecking[i][p.igIds[i]]
    del _allPlayers[p.id]


def getAllPlayersList():
    return _allPlayers.values()


class Player:
    """ Basic player class, every registered user matches a Player object contained in the dictionary
    """

    def __init__(self, name, id):
        self.__name = name
        self.__id = id
        self.__rank = 0
        self._igNames = ["N/A", "N/A", "N/A"]
        self._igIds = [0, 0, 0]
        self.__notify = False
        self.__timeout = {"time": 0, "reason": ""}
        self.__status = PlayerStatus.IS_NOT_REGISTERED
        self._hasOwnAccount = False
        self._active = None
        self._match = None
        _allPlayers[id] = self  # Add to dictionary on creation

    @classmethod
    def newFromData(cls, data):  # make a new Player object from database data
        obj = cls(data["name"], data["_id"])
        obj.__rank = data["rank"]
        if obj.__rank == 0:
            obj.__status = PlayerStatus.IS_NOT_REGISTERED
        else:
            obj.__status = PlayerStatus.IS_REGISTERED
        obj.__notify = data["notify"]
        obj.__timeout = data["timeout"]
        obj._igNames = data["igNames"]
        obj._igIds = data["igIds"]
        obj._hasOwnAccount = data["hasOwnAccount"]
        for i in range(len(obj._igIds)):
            _namesChecking[i][obj._igIds[i]] = obj
        return obj

    async def dbUpdate(self, arg):
        if arg == "notify":
            await updatePlayer(self, {"notify": self.__notify})
        elif arg == "register":
            await updatePlayer(self, {"igNames": self._igNames, "igIds": self._igIds,
                                      "rank": self.__rank, "hasOwnAccount": self._hasOwnAccount})
        elif arg == "timeout":
            await updatePlayer(self, {"timeout": self.__timeout})

    @property
    def active(self):  # "Active player" object, when player is in a match, contains more info
        return self._active

    @property
    def name(self):
        return self.__name

    @property
    def timeout(self):
        return self.__timeout["time"]

    @timeout.setter
    def timeout(self, time, reason=""):
        self.__timeout["time"] = time
        self.__timeout["reason"] = reason

    @property
    def isTimeout(self):
        return self.__timeout["time"] > int(dt.timestamp(dt.now()))

    @property
    def isNotify(self):
        return self.__notify

    @isNotify.setter
    def isNotify(self, value):
        self.__notify = value
        self.updateRole()

    def updateRole(self, i=0):
        try:
            self.roleTask.start()
        except RuntimeError:  # if task is already active
            log.warning(f"Player task conflict: {self.name}")
            pass

    @tasks.loop(count=1)
    async def roleTask(self):
        await roleUpdate(self)

    def onLobbyLeave(self):
        self.__status = PlayerStatus.IS_REGISTERED
        self.inactiveTask.stop()
        self.updateRole()

    def onLobbyAdd(self):
        self.__status = PlayerStatus.IS_LOBBIED
        self.updateRole()

    def onMatchReady(self):
        self.__status = PlayerStatus.IS_PLAYING

    def onPlayerClean(self):
        self._match = None
        self._active = None
        if not self._hasOwnAccount:
            self._igNames = ["N/A", "N/A", "N/A"]
            self._igIds = [0, 0, 0]
        self.__status = PlayerStatus.IS_REGISTERED
        self.updateRole()

    def onPicked(self):
        self.__status = PlayerStatus.IS_PICKED

    def onMatchSelected(self, m):
        self._match = m
        self.__status = PlayerStatus.IS_MATCHED
        self.inactiveTask.cancel()

    def onInactive(self, fct):
        if self.__status is PlayerStatus.IS_LOBBIED:
            self.inactiveTask.start(fct)

    def onActive(self):
        if self.status is PlayerStatus.IS_LOBBIED:
            self.inactiveTask.cancel()

    def onResign(self):
        self._active = None
        self.__status = PlayerStatus.IS_MATCHED

    @tasks.loop(minutes=cfg.AFK_TIME, delay=1, count=2)
    async def inactiveTask(self, fct):  # when inactive for cfg.AFK_TIME, execute fct
        await fct(self)

    @property
    def id(self):
        return self.__id

    @property
    def mention(self):
        return f"<@{self.__id}>"

    @property
    def rank(self):
        return self.__rank

    @rank.setter
    def rank(self, rank):
        self.__rank = rank

    @property
    def igNames(self):
        return self._igNames

    @property
    def igIds(self):
        return self._igIds

    @property
    def status(self):
        return self.__status

    @property
    def match(self):  # when in match
        return self._match

    @property
    def hasOwnAccount(self):
        return self._hasOwnAccount

    def getData(self):  # get data for database push
        data = {"_id": self.__id,
                "name": self.__name,
                "rank": self.__rank,
                "notify": self.__notify,
                "timeout": self.__timeout,
                "igNames": self._igNames,
                "igIds": self._igIds,
                "hasOwnAccount": self._hasOwnAccount
                }
        return data

    async def register(self, charList):
        """ Called when player is trying to register
            Returns whether player data was updated or not
        """
        updated = False
        if charList is None:
            if self._status == PlayerStatus.IS_NOT_REGISTERED or self._hasOwnAccount:
                updated = True
            self._igIds = [0, 0, 0]
            self._igNames = ["N/A", "N/A", "N/A"]
            if self.__status is PlayerStatus.IS_NOT_REGISTERED:
                self.__status = PlayerStatus.IS_REGISTERED
                self.__rank = 1
            self._hasOwnAccount = False
            return updated
        updated = await self._addCharacters(charList)
        if updated:
            if self.__status is PlayerStatus.IS_NOT_REGISTERED:
                self.__status = PlayerStatus.IS_REGISTERED
                self.__rank = 1
            self._hasOwnAccount = True
        return updated

    async def _addCharacters(self, charList):
        """ Add a Jaeger character to the player
            Check if characters are valid thanks to ps2 api
        """
        updated = False
        if len(charList) == 1:
            charList = [charList[0] + 'VS', charList[0] + 'NC', charList[0] + 'TR']
        if len(charList) != 3:
            raise UnexpectedError("charList is not the good size!")  # Should not happen, we checked earlier
        newIds = [0, 0, 0]
        newNames = ["N/A", "N/A", "N/A"]
        for iName in charList:
            url = 'http://census.daybreakgames.com/s:' + cfg.general['api_key'] + \
                  '/get/ps2:v2/character/?name.first_lower=' + iName.lower() + \
                  '&c:show=character_id,faction_id,name&c:resolve=world'
            jdata = await httpRequest(url)
            try:
                if jdata["returned"] == 0:
                    raise CharNotFound(iName)
            except KeyError:
                raise ApiNotReachable(url)
            try:
                world = int(jdata["character_list"][0]["world_id"])
                if world != WORLD_ID:
                    raise CharInvalidWorld(
                        jdata["character_list"][0]["name"]["first"])
                else:
                    faction = int(jdata["character_list"][0]["faction_id"])
                    currId = jdata["character_list"][0]["character_id"]
                    currName = jdata["character_list"][0]["name"]["first"]
                    if currId in _namesChecking[faction - 1]:
                        p = _namesChecking[faction - 1][currId]
                        if p != self:
                            raise CharAlreadyExists(currName, p.id)
                            
                    newIds[faction - 1] = currId
                    updated = updated or newIds[faction - 1] != self._igIds[faction - 1]
                    newNames[faction - 1] = jdata["character_list"][0]["name"]["first"]
            except IndexError:
                raise UnexpectedError("IndexError when setting player name: " + iName)  # Should not happen, we checked earlier
            except KeyError:
                raise UnexpectedError("KeyError when setting player name: " + iName)  # Don't know when this should happen either

        for i in range(len(newIds)):
            if newIds[i] == 0:
                raise CharMissingFaction(cfg.factions[i + 1])
        if updated:
            self._igIds = newIds.copy()
            self._igNames = newNames.copy()
            for i in range(len(self._igIds)):
                _namesChecking[i][self._igIds[i]] = self
        return updated


class ActivePlayer:
    """ ActivePlayer class, with more data than Player class, for when match is happening
    """

    def __init__(self, player, team):
        self.__player = player
        self.__player._active = self
        self.__kills = 0
        self.__deaths = 0
        self.__net = 0
        self.__score = 0
        self.__team = team
        self.__account = None
        self.__player.onPicked()

    def clean(self):
        self.__player.onPlayerClean()

    @property
    def name(self):
        return self.__player.name

    @property
    def status(self):
        return self.__player.status

    @property
    def id(self):
        return self.__player.id

    @property
    def hasOwnAccount(self):
        return self.__player.hasOwnAccount

    def acceptAccount(self):
        accountId = self.__account.id
        fakePlayer = getPlayer(accountId)
        if fakePlayer is None:
            raise AccountNotFound(accountId)
        self.__player._igNames = fakePlayer.igNames.copy()
        self.__player._igIds = fakePlayer.igIds.copy()

    def onMatchReady(self):
        self.__player.onMatchReady()

    def onResign(self):
        self.__player.onResign()
        return self.__player

    @property
    def mention(self):
        return self.__player.mention

    @property
    def faction(self):
        return self.__team.faction

    @property
    def igId(self):
        faction = self.__team.faction
        if faction != 0:
            return self.__player._igIds[faction - 1]

    @property
    def igName(self):
        faction = self.__team.faction
        if faction != 0:
            return self.__player._igNames[faction-1]

    @property
    def account(self):
        return self.__account

    @account.setter
    def account(self, acc):
        self.__account = acc

    @property
    def team(self):
        return self.__team

    @property
    def match(self):
        return self.__player.match

    @property
    def kills(self):
        return self.__kills

    @property
    def deaths(self):
        return self.__deaths

    @property
    def score(self):
        return self.__score

    @property
    def net(self):
        return self.__net

    def addOneKill(self, points):
        self.__kills += 1
        self.__team.addOneKill()
        self.__addPoints(points)

    def addOneDeath(self, points):
        self.__deaths += 1
        self.__team.addOneDeath()
        self.__net -= points

    def addOneTK(self):
        self.__addPoints(cfg.scores["teamkill"])

    def addOneSuicide(self):
        self.__deaths += 1
        self.__team.addOneDeath()
        self.__addPoints(cfg.scores["suicide"])

    def __addPoints(self, points):
        self.__net += points
        self.__score += points
        self.__team.addScore(points)


class TeamCaptain(ActivePlayer):
    """ Team Captain variant of the active player
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.__isTurn = False

    @property
    def isTurn(self):
        return self.__isTurn

    @isTurn.setter
    def isTurn(self, bool):
        self.__isTurn = bool
