""" Contains list of all possible bases
    Contains map selection object when searching for a map
"""

import modules.config as cfg
from modules.enumerations import SelStatus
from modules.exceptions import ElementNotFound, UserLackingPermission
from display import send
from modules.tools import date_parser
from modules.reactions import ReactionHandler, add_handler, rem_handler

from lib.tasks import loop

from logging import getLogger
from gspread import service_account
from datetime import datetime as dt
from datetime import timezone as tz
from datetime import timedelta as tdelta
from numpy import array as np_array
from asyncio import get_event_loop
from re import compile as reg_compile, sub as reg_sub
from random import randint

log = getLogger(__name__)

_allMapsList = list()
mainmap_pool = list()

MAX_SELECTED = 15

_mapSelectionsDict = dict()

def get_map_selection(id):
    sel = _mapSelectionsDict.get(id)
    if sel is None:
        raise ElementNotFound(id)
    return sel

def identify_map_from_name(string):
    # Regex magic
    pattern = reg_compile("[^a-zA-Z0-9 ]")
    string = reg_sub(" {2,}", " ", pattern.sub('', string)).strip()
    results = list()
    for map in _allMapsList:
        if string.lower() in map.name.lower():
            results.append(map)
    if len(results) == 1:
        return results[0]
    if len(results) > 1:
        temp = results.copy()
        results.clear()
        for map in temp:
            if map.pool:
                results.append(map)
        if len(results) == 1:
            return map

class Map:
    def __init__(self, data):
        self.__id = data["_id"]
        self.__name = data["facility_name"]
        self.__zoneId = data["zone_id"]
        self.__typeId = data["type_id"]
        self.__inPool = data["in_map_pool"]
        if self.__inPool:
            mainmap_pool.append(self)
        _allMapsList.append(self)

    def get_data(self):  # get data for database push
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


class MapSelection:

    _secretFile = None

    @classmethod
    def init(cls, secret_file):
        cls._secretFile = secret_file

    @classmethod
    def new_from_id(cls, match_id, map_id):
        obj = cls(match_id)
        obj.__id = match_id
        i = 0
        while _allMapsList[i].id != map_id:
            i+=1
        obj.__selection = [_allMapsList[i]]
        obj.__selected = _allMapsList[i]
        obj.__status = SelStatus.IS_CONFIRMED
        return obj

    def __init__(self, id, map_list=_allMapsList):
        self.__id = id
        self.__booked = list()
        self._getBookedFromCalendar.start()
        self.__selection = list()
        self.__selected = None
        self.__allMaps = map_list
        self.__status = SelStatus.IS_EMPTY
        _mapSelectionsDict[self.__id] = self
        self.__nav = MapNavigator(self)

    @loop(count=1)
    async def _getBookedFromCalendar(self):
        loop = get_event_loop()
        await loop.run_in_executor(None, self.__getBooked)

    def __getBooked(self):  # runs on class init, saves a list of booked maps at the time of init to self.booked
        try:
            date_rng_start = date_rng_end = None
            gc = service_account(filename=type(self)._secretFile)
            sh = gc.open_by_key(cfg.database["jaeger_cal"])
            ws = sh.worksheet("Current")
            cal_export = np_array(ws.get_all_values())
            date_col = cal_export[:, 0]
            for index, value in enumerate(date_col):
                if not date_rng_start and value == dt.now(tz.utc).strftime('%b-%d'):  # gets us the header for the current date section in the google sheet
                    date_rng_start = index + 1
                    continue
                if value == (dt.now(tz.utc) + tdelta(days=1)).strftime('%b-%d'):  # gets us the header for tomorrow's date in the sheet
                    date_rng_end = index  # now we know the range on the google sheet to look for base availability
                    break
            assert date_rng_start and date_rng_end

            today_bookings = cal_export[date_rng_start:date_rng_end, ]

            for booking in today_bookings:
                try:
                    start_time = date_parser(booking[10])  # 45 mins before start of reservation
                    if booking[11] != "":
                        end_time = date_parser(booking[11])
                    else:
                        end_time = date_parser(booking[9])
                    if start_time <= dt.now(tz.utc) <= end_time:
                        splitting_chars = ['/', ',', '&', '(', ')']
                        booked_maps = booking[3]
                        for sc in splitting_chars:
                            booked_maps = booked_maps.replace(sc, ';')
                        booked_maps = [identify_map_from_name(map) for map in booked_maps.split(";")]
                        for booked in booked_maps:
                            if booked is not None and booked not in self.__booked:
                                print(booked.name)
                                self.__booked.append(booked)
                except ValueError as e:
                    log.warning(f"Skipping invalid line in Jaeger Calendar:\n{booking}\nError: {e}")
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
            self.__status = SelStatus.IS_SELECTED
            return
        if len(self.__selection) == 0:
            self.__status = SelStatus.IS_EMPTY
            return
        self.__status = SelStatus.IS_SELECTION

    async def do_selection_process(self, ctx, args):
        if self.__status is SelStatus.IS_EMPTY and self.is_small_pool:
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
        if self.__status == SelStatus.IS_SELECTION:
            await send("MAP_DISPLAY_LIST", ctx, sel=self)
            return
        # If successfully selected:
        return self.__selected

    def is_map_booked(self, map):
        return map in self.__booked

    @property
    def navigator(self):
        return self.__nav

    @property
    def string_list(self):
        result = list()
        if len(self.__selection) > 0:
            map_list = self.__selection
        elif self.is_small_pool:
            map_list = self.__allMaps
        else:
            return result
        for i in range(len(map_list)):
            map = map_list[i]
            if self.is_map_booked(map):
                map_string = f"~~{map.name}~~"
            else:
                map_string = f"{map.name}"
            result.append(f"**{str(i+1)}**: {map_string}")
        return result

    @property
    def current_list(self):
        if len(self.__selection) > 0:
            map_list = self.__selection
        elif self.is_small_pool:
            map_list = self.__allMaps
        else:
            map_list = list()
        return map_list

    @property
    def is_small_pool(self):
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

    @property
    def is_booked(self):
        return self.__selected in self.__booked

    def confirm(self):
        if self.__status is SelStatus.IS_SELECTED:
            self.__status = SelStatus.IS_CONFIRMED
            return True
        return False

    def clean(self):
        del _mapSelectionsDict[self.__id]


class MapNavigator:
    def __init__(self, sel):
        self.__mapSel = sel
        try:
            self.__index = randint(0, len(sel.current_list)-1)
        except ValueError:
            self.__index = 0
        self.__reactionHandler = ReactionHandler()
        self.__reactionHandler.set_reaction("◀️", self.check_auth, self.go_left, self.refresh_message)
        self.__reactionHandler.set_reaction("⏺️", self.check_auth, self.select, self.refresh_message)
        self.__reactionHandler.set_reaction("▶️", self.check_auth, self.go_right, self.refresh_message)
        self.__reactionHandler.set_reaction("🔀", self.check_auth, self.shuffle, self.refresh_message)
        self.__msg = None

    @property
    def current(self):
        map_list = self.__mapSel.current_list
        if len(map_list) == 0:
            return
        self.__index = self.__index % len(map_list)
        return map_list[self.__index]

    def clean(self):
        rem_handler(self.__msg.id)

    async def set_msg(self, msg):
        self.__msg = msg
        add_handler(msg.id, self.__reactionHandler)
        await self.__reactionHandler.auto_add_reactions(msg)

    def go_right(self, *args):
        self.__index += 1

    def go_left(self, *args):
        self.__index -= 1

    def shuffle(self, *args):
        self.__index = randint(0, len(self.__mapSel.current_list)-1)

    def select(self, *args):
        pass

    def check_auth(self, reaction, player):
        if player.active and player.active.is_captain:
            return
        raise UserLackingPermission

    async def refresh_message(self, *args):
        pass
        #await self.__msg.edit(content=self.__msg.content, embed = map_pool(self.__msg, sel=self.__mapSel))

