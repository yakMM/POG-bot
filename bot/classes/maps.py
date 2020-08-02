""" Contains list of all possible bases
    Contains map selection object when searching for a map
"""

import modules.config as cfg
from modules.enumerations import SelStatus
from modules.exceptions import ElementNotFound
from modules.display import send

_allMapsList = list()

MAX_SELECTED = 15

_mapSelectionsDict = dict()

def getMapSelection(id):
    sel = _mapSelectionsDict.get(id)
    if sel == None:
        raise ElementNotFound(id)
    return sel

class Map():
    def __init__(self,data):
        self.__id = data["_id"]
        self.__name = data["facility_name"]
        self.__zoneId = data["zone_id"]
        self.__typeId = data["type_id"]
        _allMapsList.append(self)

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
    def __init__(self, id):
        self.__id = id
        self.__selection = list()
        self.__selected = None
        self.__status = SelStatus.IS_EMPTY
        _mapSelectionsDict[self.__id] = self

    def selectFromIdList(self, ids):
        self.__selection.clear()
        if len(ids) > MAX_SELECTED:
            self.__status = SelStatus.IS_TOO_MUCH
            return
        for map in _allMapsList:
            for id in ids:
                if id == map.id:
                    self.__selection.append(map)
                    break
        self.__status = SelStatus.IS_SELECTION

    def toString(self):
        result=""
        for i in range(len(self.__selection)):
            result+=f"\n**{str(i+1)}**: " + self.__selection[i].name
        return result


    def __doSelection(self, args):
        if self.__status == SelStatus.IS_SELECTION and len(args) == 1 and args[0].isnumeric():
            index = int(args[0])
            if index > 0 and index <= len(self.__selection):
                self.__selected = self.__selection[index-1]
                self.__status = SelStatus.IS_SELECTED
            return
        arg=" ".join(args)
        self.__selection.clear()
        for map in _allMapsList:
            if len(self.__selection) > MAX_SELECTED:
                self.__status = SelStatus.IS_TOO_MUCH
                return
            if arg.lower() in map.name.lower():
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
        if len(args) == 0:
            if self.__status == SelStatus.IS_SELECTION:
                await send("MAP_DISPLAY_LIST", ctx, sel=self)
                return
            if self.__status == SelStatus.IS_SELECTED:
                await send("MAP_SELECTED", ctx, self.__map.name)
                return
            await send("MAP_HELP", ctx)
            return
        if len(args) == 1 and args[0].lower() == "help":
                await send("MAP_HELP", ctx)
                return
        self.__doSelection(args)
        if self.__status == SelStatus.IS_EMPTY:
            await send("MAP_NOT_FOUND", ctx)
            return
        if self.__status == SelStatus.IS_TOO_MUCH:
            await send("MAP_TOO_MUCH", ctx)
            return
        if self.__status == SelStatus.IS_SELECTION:
            await send("MAP_DISPLAY_LIST", ctx, sel=self)
            return

    @property
    def map(self):
        return self.__selected


    @property
    def selection(self):
        return self.__selection

    @property
    def id(self):
        return self.__id

    @property
    def status(self):
        return self.__status
    
    def confirm(self):
        if self.__status == SelStatus.IS_SELECTED:
            self.__status = SelStatus.IS_CONFIRMED
            return True
        return False

    def clean(self):
        del _mapSelectionsDict[self.__id]