""" Contains list of all possible bases
    Contains map selection object when searching for a map
"""

import modules.config as cfg
from modules.enumerations import SelStatus
from modules.exceptions import ElementNotFound
from modules.display import send

_allMapsList = list()
mainMapPool = list()

MAX_SELECTED = 15

_mapSelectionsDict = dict()


def getMapSelection(id):
    sel = _mapSelectionsDict.get(id)
    if sel is None:
        raise ElementNotFound(id)
    return sel


class Map():
    def __init__(self, data):
        self.__id = data["_id"]
        self.__name = data["facility_name"]
        self.__zoneId = data["zone_id"]
        self.__typeId = data["type_id"]
        self.__inPool = data["in_map_pool"]
        if self.__inPool:
            mainMapPool.append(self)
        _allMapsList.append(self)

    def getData(self):  # get data for database push
        data = {"_id": self.__id,
                "facility_name": self.__name,
                "zone_id": self.__zoneId,
                "type_id": self.__typeId,
                "in_map_pool": self.__inPool
                }
        return data

    @property
    def pool(self):
        return self.__inPool

    @pool.setter
    def pool(self, bl):
        self.__inPool = bl

    @property
    def id(self):
        return self.__id

    @property
    def name(self):
        name = self.__name
        if self.__typeId in cfg.facilitiy_suffix:
            name += f" {cfg.facilitiy_suffix[self.__typeId]}"
        return name


class MapSelection():
    def __init__(self, id, mapList=_allMapsList):
        self.__id = id
        self.__selection = list()
        self.__selected = None
        self.__allMaps = mapList
        self.__status = SelStatus.IS_EMPTY
        _mapSelectionsDict[self.__id] = self

    @classmethod
    def newFromId(cls, matchId, mapId):
        obj = cls(matchId)
        obj.__id = matchId
        i = 0
        while _allMapsList[i].id != mapId:
            i+=1
        obj.__selection = [_allMapsList[i]]
        obj.__selected = _allMapsList[i]
        obj.__status = SelStatus.IS_CONFIRMED
        return obj

    def __doSelection(self, args):
        if self.__status is SelStatus.IS_SELECTION and len(args) == 1 and args[0].isnumeric():
            index = int(args[0])
            if index > 0 and index <= len(self.__selection):
                self.__selected = self.__selection[index-1]
                self.__status = SelStatus.IS_SELECTED
            return
        arg = " ".join(args)
        self.__selection.clear()
        for map in self.__allMaps:
            if len(self.__selection) > MAX_SELECTED:
                self.__status = SelStatus.IS_TOO_MUCH
                return
            if arg in map.name.lower():
                self.__selection.append(map)
        if len(self.__selection) == 1:
            self.__selected = self.__selection[0]
            self.__status = SelStatus.IS_SELECTED
            return
        if len(self.__selection) == 0:
            self.__status = SelStatus.IS_EMPTY
            return
        self.__status = SelStatus.IS_SELECTION

    async def doSelectionProcess(self, ctx, args):
        if self.__status is SelStatus.IS_EMPTY and self.isSmallPool:
            self.__status = SelStatus.IS_SELECTION
            self.__selection = self.__allMaps.copy()
        if len(args) == 0:
            if self.__status is SelStatus.IS_SELECTION:
                await send("MAP_DISPLAY_LIST", ctx, sel=self)
                return
            if self.__status is SelStatus.IS_SELECTED:
                await send("MAP_SELECTED", ctx, self.__selected.name)
                return
            await send("MAP_HELP", ctx)
            return
        if len(args) == 1 and args[0] == "help":
            await send("MAP_HELP", ctx)
            return
        self.__doSelection(args)
        if self.__status is SelStatus.IS_EMPTY:
            await send("MAP_NOT_FOUND", ctx)
            return
        if self.__status is SelStatus.IS_TOO_MUCH:
            await send("MAP_TOO_MUCH", ctx)
            return
        if self.__status is SelStatus.IS_SELECTION:
            await send("MAP_DISPLAY_LIST", ctx, sel=self)
            return
        # If successfully selected:
        return self.__selected

    @property
    def stringList(self):
        result = list()
        if len(self.__selection) > 0:
            for i in range(len(self.__selection)):
                result.append(f"**{str(i+1)}**: " + self.__selection[i].name)
        elif self.isSmallPool:
            for i in range(len(self.__allMaps)):
                result.append(f"**{str(i+1)}**: " + self.__allMaps[i].name)
        return result

    @property
    def isSmallPool(self):
        return len(self.__allMaps) <= MAX_SELECTED

    @property
    def map(self):
        return self.__selected

    @property
    def id(self):
        return self.__id

    @property
    def status(self):
        return self.__status

    def confirm(self):
        if self.__status is SelStatus.IS_SELECTED:
            self.__status = SelStatus.IS_CONFIRMED
            return True
        return False

    def clean(self):
        del _mapSelectionsDict[self.__id]
