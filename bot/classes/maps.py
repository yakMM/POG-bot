""" Contains list of all possible bases
    Contains map selection object when searching for a map
"""

import modules.config as cfg
from modules.enumerations import SelStatus
from modules.exceptions import ElementNotFound
from modules.display import send

_allMapsList = list()

MAX_SELECTED = 15

_mapSelections = dict()


def getMapSelection(id):
    sel = _mapSelections.get(id)
    if sel == None:
        raise ElementNotFound(id)
    return sel

async def doSelectionProcess(id, ctx, *args):
    try:
        sel = getMapSelection(id)
    except ElementNotFound:
        if len(args) == 0:
            await send("MAP_HELP", ctx)
            return
        sel = MapSelection(id)
    if len(args) == 0:
        if sel.status == SelStatus.IS_SELECTION:
            await send("MAP_DISPLAY_LIST", ctx, sel=sel)
            return
        if sel.status == SelStatus.IS_SELECTED:
            await send("MAP_SELECTED", ctx, sel.map.name)
            return
        await send("MAP_HELP", ctx)
        return
    if len(args) == 1 and args[0].lower() == "help":
            await send("MAP_HELP", ctx)
            return
    if args[0].isnumeric() and len(args) == 1:
        res = int(args[0])
        sel.selectIndex(res)
    else:
        req=" ".join(args)
        sel.doSelection(req)
    if sel.status == SelStatus.IS_EMPTY:
        await send("MAP_NOT_FOUND", ctx)
        return
    if sel.status == SelStatus.IS_TOO_MUCH:
        await send("MAP_TOO_MUCH", ctx)
        return
    if sel.status == SelStatus.IS_SELECTION:
        await send("MAP_DISPLAY_LIST", ctx, sel=sel)
        return
    if sel.status == SelStatus.IS_SELECTED:
        return sel.map

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
        _mapSelections[id] = self

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


    def doSelection(self, arg):
        self.__selection.clear()
        for map in _allMapsList:
            if len(self.__selection) > MAX_SELECTED:
                self.__status = SelStatus.IS_TOO_MUCH
                return
            if map.name.lower().find(arg.lower()) != -1:
                self.__selection.append(map)
        if len(self.__selection) == 1:
            self.__selected = self.__selection[0]
            self.__status = SelStatus.IS_SELECTED
            return
        if len(self.__selection) == 0:
            self.__status = SelStatus.IS_EMPTY
            return
        self.__status = SelStatus.IS_SELECTION

    def selectIndex(self, index):
        if self.__status != SelStatus.IS_SELECTION:
            return
        if index > 0 and index <= len(self.__selection):
            self.__selected = self.__selection[index-1]
            self.__status = SelStatus.IS_SELECTED
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