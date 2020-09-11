""" Basic team object, should be explicit
"""


class Team:
    def __init__(self, id, name, match):
        self.__id = id
        self.__name = name
        self.__players = list()
        self.__score = 0
        self.__deaths = 0
        self.__kills = 0
        self.__faction = 0
        self.__cap = 0
        self.__match = match

    @property
    def id(self):
        return self.__id

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

    def addScore(self, points):
        self.__score += points

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

    def addOneKill(self):
        self.__kills += 1

    def addOneDeath(self):
        self.__deaths += 1

    def addPlayer(self, cls, player):
        active = cls(player, self)
        self.__players.append(active)

    def onMatchReady(self):
        for p in self.__players:
            p.onMatchReady()
