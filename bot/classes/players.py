"""Contains player classes
"""
# Others
import enum

# Custom modules
import modules.config as cfg
from modules.asynchttp import request as httpRequest
from modules.exceptions import UnexpectedError, ElementNotFound, StatusNotAllowed, CharNotFound, CharInvalidWorld, CharMissingFaction, CharAlreadyExists
from modules.enumerations import PlayerStatus
from discord.ext import tasks

WORLD_ID = 19 # Jaeger ID

# temp, will be in config file later
scoring =	{
  "tk": -2,
  "suicide": -2,
  "kill": 1
}

_allPlayers = dict()
_namesChecking=[dict(),dict(),dict()] # to store VS, NC and TR names to check for duplicates

def getPlayer(id):
    player = _allPlayers.get(id)
    if player == None:
        raise ElementNotFound(id)
    return player

def removePlayer(id):
    if id not in _allPlayers:
        raise ElementNotFound(id)
    del _allPlayers[id]

class Player():
    """ Basic player class, every registered user matches a Player object contained in the dictionary
    """

    def __init__(self, name, id):
        self._name = name
        self._id = id
        self._rank = 0
        self._igNames = ["N/A", "N/A", "N/A"]
        self._igIds = [0,0,0]
        self._status = PlayerStatus.IS_NOT_REGISTERED
        self._hasOwnAccount = False
        self._active = None
        self._match = None
        _allPlayers[id] = self # Add to dictionary on creation

    @classmethod
    def newFromData(cls, data): # make a new Player object from database data
        obj = cls(data["name"], data["_id"])
        obj._status=PlayerStatus.IS_REGISTERED
        obj._rank = data["rank"]
        obj._igNames = data["igNames"]
        obj._igIds = data["igIds"]
        obj._hasOwnAccount = data["hasOwnAccount"]
        for i in range(len(obj._igIds)):
            _namesChecking[i][obj._igIds[i]] = obj
        return obj

    @property
    def active(self): # "Active player" object, when player is in a match, contains more info
        return self._active

    def clean(self):
        self._status = PlayerStatus.IS_REGISTERED
        self._match = None
        self._active = None
        if not self._hasOwnAccount:
            self._igNames = ["N/A", "N/A", "N/A"]
            self._igIds = [0,0,0]

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._id
    
    @property
    def mention(self):
        return f"<@{self._id}>" 

    @property
    def rank(self):
        return self._rank

    @rank.setter
    def rank(self, rank):
        self._rank = rank

    @property
    def igNames(self):
        return self._igNames

    @property
    def igIds(self):
        return self._igIds

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        if status in (PlayerStatus.IS_NOT_REGISTERED, PlayerStatus.IS_MATCHED): # these status are set automatically from inside the class, can't set them from outside
            raise StatusNotAllowed(status.name)
            return
        self._status = status

    @property
    def match(self): # when in match
        return self._match

    @match.setter
    def match(self, m):
        self.onInactive.cancel() # don't want player to be kicked because becoming offline if in match
        self._match = m
        self._status = PlayerStatus.IS_MATCHED

    @property
    def hasOwnAccount(self):
        return self._hasOwnAccount

    def getData(self): # get data for database push
        data = {"_id" : self._id,
                "name" : self._name,
                "rank" : self._rank,
                "igNames" : self._igNames,
                "igIds" : self._igIds,
                "hasOwnAccount" : self._hasOwnAccount
                }
        return data


    async def register(self, charList):
        """ Called when player is trying to register
            Returns wether player data was updated or not
        """
        updated = False
        if charList == None:
            if(self._status == PlayerStatus.IS_NOT_REGISTERED or self._hasOwnAccount):
                updated = True
            self._igIds = [0,0,0]
            self._igNames = ["N/A", "N/A", "N/A"]
            if self._status == PlayerStatus.IS_NOT_REGISTERED:
                self._status = PlayerStatus.IS_REGISTERED
            self._hasOwnAccount = False
            return updated
        updated = await self._addCharacters(charList)
        if updated:
            if self._status == PlayerStatus.IS_NOT_REGISTERED:
                self._status = PlayerStatus.IS_REGISTERED
            self._hasOwnAccount = True
        return updated

    async def _addCharacters(self, charList):
        """ Add a Jaeger character to the player
            Check if characters are valid thanks to ps2 api
        """
        updated = False
        if len(charList)==1:
            charList=[charList[0]+'VS',charList[0]+'NC',charList[0]+'TR']
        if len(charList) != 3:
            raise UnexpectedError("charList is not the good size!") # Should not happen, we checked earlier
        newIds = [0,0,0]
        newNames = ["N/A", "N/A", "N/A"]
        for iName in charList:
            url = 'http://census.daybreakgames.com/s:'+cfg.general['api_key']+'/get/ps2:v2/character/?name.first_lower='+iName.lower()+'&c:show=character_id,faction_id,name&c:resolve=world'
            jdata = await httpRequest(url)
            if jdata["returned"]==0:
                raise CharNotFound(iName)
            else:
                try:
                    world = int(jdata["character_list"][0]["world_id"])
                    if world != WORLD_ID:
                        raise CharInvalidWorld(jdata["character_list"][0]["name"]["first"])
                    else:
                        faction = int(jdata["character_list"][0]["faction_id"])
                        currId = jdata["character_list"][0]["character_id"]
                        currName = jdata["character_list"][0]["name"]["first"]
                        if currId in _namesChecking[faction-1]:
                            p = _namesChecking[faction-1][currId]
                            if p != self:
                                raise CharAlreadyExists(currName, p.id)
                        newIds[faction-1] = currId
                        updated = updated or newIds[faction-1] != self._igIds[faction-1]
                        newNames[faction-1] = jdata["character_list"][0]["name"]["first"]
                except IndexError:
                    raise UnexpectedError("IndexError when setting player name: "+iName) # Should not happen, we checked earlier
                except KeyError:
                    raise UnexpectedError("KeyError when setting player name: "+iName) # Don't know when this should happen either
        for i in range(len(newIds)):
            if newIds[i] == 0:
                raise CharMissingFaction(cfg.factions[i+1])
        if updated:
            self._igIds = newIds.copy()
            self._igNames = newNames.copy()
            for i in range(len(self._igIds)):
                _namesChecking[i][self._igIds[i]] = self
        return updated

    @tasks.loop(minutes=cfg.AFK_TIME, count=2)
    async def onInactive(self, fct): # when inactive for cfg.AFK_TIME, execute fct
        if self.onInactive.hasJustBecome:
            self.onInactive.hasJustBecome = False
            return
        await fct(self)


class ActivePlayer:
    """ ActivePlayer class, with more data than Player class, for when match is happening
    """

    def __init__(self, player, team):
        self.__player = player
        self.__player._active = self
        self.__kills=0
        self.__deaths=0
        self.__net=0
        self.__score=0
        self.__team = team
        self.__account = None

    def clean(self):
        self.__player.clean()

    @property
    def name(self):
        return self.__player.name

    @property
    def status(self):
        return self.__player.status

    @status.setter
    def status(self, status):
        self.__player.status = status

    @property
    def id(self):
        return self.__player.id

    @property
    def hasOwnAccount(self):
        return self.__player.hasOwnAccount

    def acceptAccount(self):
        accountId = self.__account.id
        fakePlayer = getPlayer(accountId)
        if fakePlayer == None:
            raise AccountNotFound(accountId)
        self.__player._igNames = fakePlayer.igNames.copy()
        self.__player._igIds = fakePlayer.igIds.copy()



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
            return self.__player._igIds[faction-1]

    @property
    def igName(self):
        faction = self.__team.faction
        if faction != 0:
            return self.__player._igIds[faction-1]

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
        self.__kills+=1
        self.__addPoints(points)

    def addOneDeath(self, points):
        self.__deaths+=1
        self.__net-=points

    def addOneTK(self):
        self.__addPoints(scoring["tk"])

    def addOneSuicide(self):
        self.__deaths+=1
        self.__addPoints(scoring["suicide"])

    def __addPoints(self, points):
        self.__net+=points
        self.__score+=points


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

