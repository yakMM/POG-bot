""" Contains list of all possible bases
    Contains map selection object when searching for a map
"""

import modules.config as cfg
from modules.enumerations import SelStatus
from modules.exceptions import ElementNotFound
from modules.display import send
from logging import getLogger
from gspread import service_account
from gspread.exceptions import APIError
import datetime as dt
import numpy as np

log = getLogger(__name__)

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
        if self.__typeId in cfg.facility_suffix:
            name += f" {cfg.facility_suffix[self.__typeId]}"
        return name


def createJeagerCalObj(secretFile):
    global jaeger_cal_obj
    jaeger_cal_obj = JaegerCalendarHandler(secretFile)


class JaegerCalendarHandler:
    def __init__(self, secretFile):
        self._secretFile = secretFile
        self.gc = service_account(filename=secretFile)
        self.sh = self.gc.open_by_key(cfg.database["jaeger_cal"])


class MapSelection():
    def __init__(self, id, mapList=_allMapsList):
        self.__id = id
        self.booked = list()
        self.get_booked(mapList)
        self.__selection = list()
        self.__selected = None
        self.__allMaps = mapList
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
        result = ""
        for i in range(len(self.__selection)):
            result += f"\n**{str(i + 1)}**: " + self.__selection[i].name
        return result

    def is_available(self, map):
        available = True
        if map in self.booked:
            available = False
        return available

    def select_available(self, maps):  # returns available maps from a list of maps
        available = list()
        for map in maps:
            if self.is_available(map):
                available.append(map)
        return available

    def get_booked(self, maplist):  # runs on class init, saves a list of booked maps at the time of init to self.booked
        try:
            date_rng_start = date_rng_end = None
            ws = jaeger_cal_obj.sh.worksheet("Current")
            cal_export = np.array(ws.get_all_values())
            date_col = cal_export[:, 0]
            for index, value in enumerate(date_col):
                if not date_rng_start and value == dt.datetime.utcnow().strftime('%b-%d'):  # gets us the header for the current date section in the google sheet
                    date_rng_start = index + 1
                    continue
                if value == (dt.datetime.utcnow() + dt.timedelta(days=1)).strftime('%b-%d'):  # gets us the header for tomorrow's date in the sheet
                    date_rng_end = index  # now we know the range on the google sheet to look for base availability
                    break
            assert date_rng_start and date_rng_end

            today_bookings = cal_export[date_rng_start:date_rng_end, ]

            for map in maplist:
                for booking in today_bookings:
                    booked_maps = booking[3].replace('/', ',').split(",")
                    booked_maps = [map.strip() for map in booked_maps]
                    for booked_map in booked_maps:
                        if booked_map.lower() in map.name.lower():
                            start_time = booking[10]  # 45 mins before start of reservation
                            if booking[11] != "":
                                end_time = booking[11]
                            else:
                                end_time = booking[9]
                            if start_time <= dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') <= end_time:
                                # if date formatting in google calendar hidden cells changes, this needs to be updated too.
                                self.booked.append(map)
        except AssertionError:
            log.warning(f"Unable to find date range in Jaeger calendar for today's date. Returned: '{date_rng_start}' to '{date_rng_end}'")
        except Exception as e:
            log.error(f"Uncaught exception getting booked maps from jaeger calendar\n{str(e)}")  # delete when done testing
        return

    def __doSelection(self, args):
        if self.__status is SelStatus.IS_SELECTION and len(args) == 1 and args[0].isnumeric():
            index = int(args[0])
            if 0 < index <= len(self.__selection):
                self.__selected = self.__selection[index - 1]
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
            if self.is_available(self.__selected):
                self.__status = SelStatus.IS_SELECTED
                return
            else:
                self.__status = SelStatus.IS_BOOKED
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
        if self.__status == SelStatus.IS_BOOKED:
            await send("MAP_BOOKED", ctx, self.__selected.name)
            self.__status = SelStatus.IS_SELECTED
            return
        if self.__status == SelStatus.IS_SELECTION:
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
