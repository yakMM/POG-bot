""" Basic team object, should be explicit
"""

from modules.enumerations import PlayerStatus

class Team:
    def __init__(self, id, name, match):
        self.__id = id
        self.__name = name
        self.__players=list()
        self.__score=0
        self.__faction=0
        self.__cap=0
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
    def faction(self,faction):
        self.__faction=faction

    @property
    def score(self):
        return self.__score

    def addScore(self, points):
        self.__score+=points

    @property
    def cap(self):
        return self.__cap

    @property
    def playerPings(self):
        pings = [f"<@{p.id}>" for p in self.__players[1:]]
        return pings

    @property
    def allPings(self):
        pings = [f"<@{p.id}>" for p in self.__players]
        return " ".join(pings)

    @property
    def captain(self):
        return self.__players[0]

    def addCap(self, points):
        self.__cap+=points
        self.__score+=points

    def addPlayer(self, cls, player):
        active = cls(player, self)
        self.__players.append(active)
        active.status = PlayerStatus.IS_PICKED

    def matchReady(self):
        for p in self.__players:
            p.status = PlayerStatus.IS_PLAYING


