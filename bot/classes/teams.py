""" Basic team object, should be explicit
"""

from modules.enumerations import PlayerStatus
from classes.players import ActivePlayer # ok


class Team:
    def __init__(self, id, name, match):
        self.__id = id
        self.__name = name
        self.__players = list()
        self.__score = 0
        self.__net = 0
        self.__deaths = 0
        self.__kills = 0
        self.__faction = 0
        self.__cap = 0
        self.__match = match

    @classmethod
    def newFromData(cls, i, data, match):
        obj = cls(i, data["name"], match)
        obj.__faction = data["faction_id"]
        obj.__score = data["score"]
        obj.__net = data["net"]
        obj.__deaths = data["deaths"]
        obj.__kills = data["kills"]
        obj.__cap = data["cap_points"]
        for pData in data["players"]:
            obj.__players.append(ActivePlayer.newFromData(pData, obj))
        return obj

    def getData(self):
        playersData = list()
        for p in self.__players:
            playersData.append(p.getData())
        data = {"name": self.__name,
                "faction_id": self.__faction,
                "score": self.__score,
                "net": self.__net,
                "deaths": self.deaths,
                "kills": self.__kills,
                "cap_points": self.__cap,
                "players": playersData
                }
        return data

    @property
    def id(self):
        return self.__id

    @property
    def igString(self):
        pString = ",".join(p.igName for p in self.__players)
        return f"{self.__name}: `{pString}`"

    @property
    def name(self):
        return self.__name

    @property
    def players(self):
        return self.__players

    @property
    def faction(self):
        return self.__faction

    @faction.setter
    def faction(self, faction):
        self.__faction = faction

    @property
    def score(self):
        return self.__score

    @property
    def net(self):
        return self.__net

    @property
    def cap(self):
        return self.__cap
    
    @property
    def kills(self):
        return self.__kills
    
    @property
    def deaths(self):
        return self.__deaths

    @property
    def playerPings(self):
        # Excluding captain
        pings = [p.mention for p in self.__players[1:]]
        return pings

    @property
    def allPings(self):
        # All players with captain
        pings = [p.mention for p in self.__players]
        return pings

    @property
    def captain(self):
        return self.__players[0]

    @property
    def isPlayers(self):
        return len(self.__players) > 1
    
    def clear(self):
        self.__players.clear()

    def addCap(self, points):
        self.__cap += points
        self.__score += points
        self.__net += points

    def addScore(self, points):
        self.__score += points

    def addNet(self, points):
        self.__net += points

    def addOneKill(self):
        self.__kills +=1

    def addOneDeath(self):
        self.__deaths +=1

    def addPlayer(self, cls, player):
        active = cls(player, self)
        self.__players.append(active)
    
    def onTeamReady(self):
        for aP in self.__players:
            aP.onTeamReady()

    def onMatchReady(self):
        for p in self.__players:
            p.onMatchReady()

    def onPlayerSub(self, subbed, newPlayer):
        i = 0
        while self.__players[i] is not subbed:
            i+=1
        active = type(subbed)(newPlayer, self)
        self.__players[i] = active
