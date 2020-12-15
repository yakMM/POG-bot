""" Contains list of all possible bases
    Contains map selection object when searching for a map
"""

import modules.config as cfg
from modules.enumerations import SelStatus
from modules.exceptions import ElementNotFound, UserLackingPermission
from display import send, SendCtx, edit
from modules.tools import date_parser
from modules.reactions import ReactionHandler, add_handler, rem_handler
from modules.roles import is_admin

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

log = getLogger("pog_bot")

_all_maps_list = list()
main_maps_pool = list()

MAX_SELECTED = 15


def identify_map_from_name(string):
    # Regex magic
    if len(string) == 0:
        return
    pattern = reg_compile("[^a-zA-Z0-9 ]")
    string = reg_sub(" {2,}", " ", pattern.sub('', string)).strip()
    results = list()
    for map in _all_maps_list:
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
            return results[0]

class Map:

    @classmethod
    def get(this, m_id : int):
        if m_id not in _all_maps_list:
            raise ElementNotFound(m_id)
        return _all_maps_list[m_id]

    def __init__(self, data):
        self.__id = data["_id"]
        self.__name = data["name"]
        self.__zone_id = data["zone_id"]
        self.__type_id = data["type_id"]
        self.__in_pool = data["in_map_pool"]
        if self.__in_pool:
            main_maps_pool.append(self)
        _all_maps_list.append(self)

    def get_data(self):  # get data for database push
        data = {"_id": self.__id,
                "name": self.__name,
                "zone_id": self.__zone_id,
                "type_id": self.__type_id,
                "in_map_pool": self.__in_pool
                }
        return data

    @property
    def pool(self):
        return self.__in_pool

    @pool.setter
    def pool(self, bl):
        self.__in_pool = bl

    @property
    def id(self):
        return self.__id

    @property
    def name(self):
        name = self.__name
        if self.__type_id in cfg.facility_suffix:
            name += f" {cfg.facility_suffix[self.__type_id]}"
        return name


class MapSelection:

    _secret_file = None

    @classmethod
    def init(cls, secret_file):
        cls._secret_file = secret_file

    @classmethod
    def new_from_id(cls, match, map_id):
        obj = cls(match, from_data = True)
        i = 0
        while _all_maps_list[i].id != map_id:
            i+=1
        obj.__selection = [_all_maps_list[i]]
        obj.__selected = _all_maps_list[i]
        obj.__status = SelStatus.IS_CONFIRMED
        return obj

    def __init__(self, match, map_pool = False, from_data = False):
        if map_pool:
            self.__all_maps = main_maps_pool
        else:
            self.__all_maps = _all_maps_list
        self.__match = match
        self.__selection = list()
        self.__selected = None
        self.__booked = list()
        self.__status = SelStatus.IS_EMPTY
        if from_data:
            return
        self.__nav = MapNavigator(self)
        self._get_booked_from_calendar.start()

    @loop(count=1)
    async def _get_booked_from_calendar(self):
        loop = get_event_loop()
        await loop.run_in_executor(None, self.__get_booked)

    def __get_booked(self):  # runs on class init, saves a list of booked maps at the time of init to self.booked
        try:
            date_rng_start = date_rng_end = None
            gc = service_account(filename=MapSelection._secret_file)
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
                                self.__booked.append(booked)
                except ValueError as e:
                    log.warning(f"Skipping invalid line in Jaeger Calendar:\n{booking}\nError: {e}")
        except AssertionError:
            log.warning(f"Unable to find date range in Jaeger calendar for today's date. Returned: '{date_rng_start}' to '{date_rng_end}'")
        except Exception as e:
            log.error(f"Uncaught exception getting booked maps from jaeger calendar\n{str(e)}")  # delete when done testing
        return

    def __do_selection(self, args):
        if self.__status is SelStatus.IS_SELECTION and len(args) == 1 and args[0].isnumeric():
            index = int(args[0])
            if 0 < index <= len(self.__selection):
                self.__selected = self.__selection[index - 1]
                self.__status = SelStatus.IS_SELECTED
            return SelStatus.IS_SELECTED
        arg = " ".join(args)
        current_list = list()
        for map in self.__all_maps:
            if len(current_list) > MAX_SELECTED:
                return SelStatus.IS_TOO_MUCH
            if arg in map.name.lower():
                current_list.append(map)
        if len(current_list) == 1:
            self.__selected = current_list[0]
            self.__status = SelStatus.IS_SELECTED
            return SelStatus.IS_SELECTED
        if len(current_list) == 0:
            return SelStatus.IS_EMPTY
        self.__selection = current_list
        self.__status = SelStatus.IS_SELECTION
        return SelStatus.IS_SELECTION

    async def on_pick_start(self):
        if self.__status is SelStatus.IS_EMPTY and self.is_small_pool:
            self.__status = SelStatus.IS_SELECTION
            self.__selection = self.__all_maps.copy()
        if self.__status is SelStatus.IS_SELECTION:
            await send("MAP_SHOW_LIST", self.__match.channel, sel=self)
            await self.__nav.reset_msg()
            return
        if self.__status is SelStatus.IS_SELECTED:
            await send("MAP_SELECTED", self.__match.channel, self.__selected.name)
            return

    async def do_selection_process(self, ctx, args):
        if self.__status is SelStatus.IS_EMPTY and self.is_small_pool:
            self.__status = SelStatus.IS_SELECTION
            self.__selection = self.__all_maps.copy()
        if len(args) == 0:
            if self.__status is SelStatus.IS_SELECTION:
                await send("MAP_SHOW_LIST", ctx, sel=self)
                await self.__nav.reset_msg()
                return
            if self.__status is SelStatus.IS_SELECTED:
                await send("MAP_SELECTED", ctx, self.__selected.name)
                return
            await send("MAP_HELP", ctx)
            return
        if len(args) == 1 and args[0] == "help":
            await send("MAP_HELP", ctx)
            return
        sel_status = self.__do_selection(args)
        if sel_status is SelStatus.IS_EMPTY:
            await send("MAP_NOT_FOUND", ctx)
            return
        if sel_status is SelStatus.IS_TOO_MUCH:
            await send("MAP_TOO_MUCH", ctx)
            return
        if sel_status == SelStatus.IS_SELECTION:
            await send("MAP_SHOW_LIST", ctx, sel=self)
            await self.__nav.reset_msg()
            return
        # If successfully selected:
        return self.__selected

    def is_map_booked(self, map):
        return map in self.__booked

    def select_by_index(self, index):
        self.__selected = self.__selection[index]
        self.__status = SelStatus.IS_SELECTED

    @property
    def navigator(self):
        return self.__nav

    @property
    def match(self):
        return self.__match

    @property
    def string_list(self):
        result = list()
        if len(self.__selection) > 0:
            map_list = self.__selection
        elif self.is_small_pool:
            map_list = self.__all_maps
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
            map_list = self.__all_maps
        else:
            map_list = list()
        return map_list

    @property
    def is_small_pool(self):
        return len(self.__all_maps) <= MAX_SELECTED

    @property
    def map(self):
        if self.status is SelStatus.IS_CONFIRMED:
            return self.__selected
        else:
            return None

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


    async def wait_confirm(self, ctx, picker):
        def confirm_map(reaction, player, user):
                if player.active and player.active is picker:
                    self.__match.confirm_map()
                else:
                    raise UserLackingPermission

        rh = ReactionHandler(rem_bot_react=True)
        rh.set_reaction('✅', confirm_map)
        msg = await send("PK_MAP_OK_CONFIRM", ctx, self.map.name, picker.mention)
        add_handler(msg.id, rh)
        await rh.auto_add_reactions(msg)


class MapNavigator:
    def __init__(self, sel):
        self.__sel = sel
        self.__match = sel.match
        self.__index = 0
        self.__current_length = 0
        self.__reaction_handler = ReactionHandler()
        self.__reaction_handler.set_reaction("◀️", self.check_auth, self.go_left, self.refresh_message)
        self.__reaction_handler.set_reaction("⏺️", self.check_auth, self.select)
        self.__reaction_handler.set_reaction("▶️", self.check_auth, self.go_right, self.refresh_message)
        self.__reaction_handler.set_reaction("🔀", self.check_auth, self.shuffle, self.refresh_message)
        self.__msg = None

    @property
    def current(self):
        if self.__sel.status is SelStatus.IS_CONFIRMED:
            return self.__sel.map
        return self.__sel.current_list[self.__index]

    @property
    def is_booked(self):
        return self.__sel.is_map_booked(self.current)

    async def __remove_msg(self):
        if self.__msg:
            rem_handler(self.__msg.id)
            await self.__msg.delete()

    async def reset_msg(self):
        await self.__remove_msg()
        try:
            self.__index = randint(0, len(self.__sel.current_list)-1)
        except ValueError:
            self.__index = 0
        self.__current_length = len(self.__sel.current_list)
        msg = await send("MAP_SHOW_POOL", self.__match.channel, sel=self.__sel)
        self.__msg = msg
        add_handler(msg.id, self.__reaction_handler)
        await self.__reaction_handler.auto_add_reactions(msg)

    def go_right(self, *args):
        self.__index += 1
        self.__index %= self.__current_length

    def go_left(self, *args):
        self.__index -= 1
        self.__index %= self.__current_length

    def shuffle(self, *args):
        # Get a new map at random
        old_index = self.__index
        # Exclude the last map
        self.__index = randint(0, self.__current_length-2)
        # So that if we get the old map, we take the last map instead
        if self.__index == old_index:
            self.__index = self.__current_length-1
        # Like so, the odds are even for all maps

    async def select(self, reaction, player, user):
        self.__sel.select_by_index(self.__index)
        ctx = SendCtx.wrap(self.__match.channel)
        ctx.author = user
        await self.__msg.clear_reactions()
        if player.active and player.active.is_captain:
            new_picker = self.__match.pick_map(player.active)
            await self.__sel.wait_confirm(ctx, new_picker)
            return
        if is_admin(user):
            self.__match.confirm_map()
            await send("MATCH_MAP_SELECTED", ctx, self.__sel.map.name, sel=self.__sel)
            return

    def check_auth(self, reaction, player, user):
        if player.active and player.active.is_captain:
            return
        if is_admin(user):
            return
        raise UserLackingPermission

    async def refresh_message(self, *args):
        await edit("MAP_SHOW_POOL", self.__msg, sel=self.__sel)

