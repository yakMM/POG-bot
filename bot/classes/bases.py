""" Contains list of all possible bases
    Contains base selection object when searching for a base
"""

import modules.config as cfg
from general.enumerations import SelStatus
from general.exceptions import ElementNotFound, UserLackingPermission
from display.strings import AllStrings as display
from display.classes import ContextWrapper
from modules.reactions import ReactionHandler, add_handler, rem_handler
from modules.roles import is_admin
from modules.jaeger_calendar import get_booked_bases

from lib.tasks import loop

from logging import getLogger

from asyncio import get_event_loop

from random import randint

log = getLogger("pog_bot")

MAX_SELECTED = 15


class Base:
    _all_bases_list = list()
    _base_pool = list()

    @classmethod
    def get(cls, m_id: int):
        if m_id not in cls._all_bases_list:
            raise ElementNotFound(m_id)
        return cls._all_bases_list[m_id]

    @classmethod
    def get_bases_from_name(cls, name):
        results = list()
        for base in cls._all_bases_list:
            if name.lower() in base.name.lower():
                results.append(base)
        return results

    @classmethod
    def get_base_from_id(cls, base_id):
        for base in cls._all_bases_list:
            if base.id == base_id:
                return base

    @classmethod
    def get_bases(cls):
        return cls._all_bases_list.copy()

    @classmethod
    def get_pool(cls):
        return cls._base_pool.copy()

    def __init__(self, data):
        self.__id = data["_id"]
        self.__name = data["name"]
        self.__zone_id = data["zone_id"]
        self.__type_id = data["type_id"]
        self.__in_pool = data["in_map_pool"]
        if self.__in_pool:
            Base._base_pool.append(self)
        Base._all_bases_list.append(self)

    def get_data(self):  # get data for database push
        data = {"_id": self.__id,
                "name": self.__name,
                "zone_id": self.__zone_id,
                "type_id": self.__type_id,
                "in_base_pool": self.__in_pool
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

    @classmethod
    def new_from_id(cls, match, base_id):
        obj = cls(match, from_data=True)
        i = 0
        base = Base.get_base_from_id(base_id)
        if base is None:
            raise ElementNotFound(base_id)
        obj.__selection = [base]
        obj.__selected = base
        obj.__status = SelStatus.IS_CONFIRMED
        return obj

    def __init__(self, match, base_pool=False, from_data=False):
        if base_pool:
            self.__all_bases = Base.get_pool()
        else:
            self.__all_bases = Base.get_bases()
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
        await loop.run_in_executor(None, get_booked_bases, Base, self.__booked)

    def __do_selection(self, args):
        if self.__status is SelStatus.IS_SELECTION and len(args) == 1 and args[0].isnumeric():
            index = int(args[0])
            if 0 < index <= len(self.__selection):
                self.__selected = self.__selection[index - 1]
                self.__status = SelStatus.IS_SELECTED
            return SelStatus.IS_SELECTED
        arg = " ".join(args)
        current_list = list()
        for base in self.__all_bases:
            if len(current_list) > MAX_SELECTED:
                return SelStatus.IS_TOO_MUCH
            if arg in base.name.lower():
                current_list.append(base)
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
            self.__selection = self.__all_bases.copy()
        if self.__status is SelStatus.IS_SELECTION:
            await display.BASE_SHOW_LIST.send(self.__match.channel, sel=self)
            await self.__nav.reset_msg()
            return
        if self.__status is SelStatus.IS_SELECTED:
            await display.BASE_SELECTED.send(self.__match.channel, self.__selected.name)
            return

    async def do_selection_process(self, ctx, args):
        if self.__status is SelStatus.IS_EMPTY and self.is_small_pool:
            self.__status = SelStatus.IS_SELECTION
            self.__selection = self.__all_bases.copy()
        if len(args) == 0:
            if self.__status is SelStatus.IS_SELECTION:
                await display.BASE_SHOW_LIST.send(ctx, sel=self)
                await self.__nav.reset_msg()
                return
            if self.__status is SelStatus.IS_SELECTED:
                await display.BASE_SELECTED.send(ctx, self.__selected.name)
                return
            await display.BASE_HELP.send(ctx)
            return
        if len(args) == 1 and args[0] == "help":
            await display.BASE_HELP.send(ctx)
            return
        sel_status = self.__do_selection(args)
        if sel_status is SelStatus.IS_EMPTY:
            await display.BASE_NOT_FOUND.send(ctx)
            return
        if sel_status is SelStatus.IS_TOO_MUCH:
            await display.BASE_TOO_MUCH.send(ctx)
            return
        if sel_status == SelStatus.IS_SELECTION:
            await display.BASE_SHOW_LIST.send(ctx, sel=self)
            await self.__nav.reset_msg()
            return
        # If successfully selected:
        return self.__selected

    def is_base_booked(self, base):
        return base in self.__booked

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
            base_list = self.__selection
        elif self.is_small_pool:
            base_list = self.__all_bases
        else:
            return result
        for i in range(len(base_list)):
            base = base_list[i]
            if self.is_base_booked(base):
                base_string = f"~~{base.name}~~"
            else:
                base_string = f"{base.name}"
            result.append(f"**{str(i + 1)}**: {base_string}")
        return result

    @property
    def current_list(self):
        if len(self.__selection) > 0:
            base_list = self.__selection
        elif self.is_small_pool:
            base_list = self.__all_bases
        else:
            base_list = list()
        return base_list

    @property
    def is_small_pool(self):
        return len(self.__all_bases) <= MAX_SELECTED

    @property
    def base(self):
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
        def confirm_base(reaction, player, user):
            if player.active and player.active is picker:
                self.__match.confirm_base()
            else:
                raise UserLackingPermission

        rh = ReactionHandler(rem_bot_react=True)
        rh.set_reaction('✅', confirm_base)
        msg = await display.PK_BASE_OK_CONFIRM.send(ctx, self.base.name, picker.mention)
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
            return self.__sel.base
        return self.__sel.current_list[self.__index]

    @property
    def is_booked(self):
        return self.__sel.is_base_booked(self.current)

    async def __remove_msg(self):
        if self.__msg:
            rem_handler(self.__msg.id)
            await self.__msg.delete()

    async def reset_msg(self):
        await self.__remove_msg()
        try:
            self.__index = randint(0, len(self.__sel.current_list) - 1)
        except ValueError:
            self.__index = 0
        self.__current_length = len(self.__sel.current_list)
        msg = await display.BASE_SHOW_POOL.send(self.__match.channel, sel=self.__sel)
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
        # Get a new base at random
        old_index = self.__index
        # Exclude the last base
        self.__index = randint(0, self.__current_length - 2)
        # So that if we get the old base, we take the last base instead
        if self.__index == old_index:
            self.__index = self.__current_length - 1
        # Like so, the odds are even for all bases

    async def select(self, reaction, player, user):
        self.__sel.select_by_index(self.__index)
        ctx = ContextWrapper.wrap(self.__match.channel)
        ctx.author = user
        await self.__msg.clear_reactions()
        if player.active and player.active.is_captain:
            new_picker = self.__match.pick_base(player.active)
            await self.__sel.wait_confirm(ctx, new_picker)
            return
        if is_admin(user):
            self.__match.confirm_base()
            await display.MATCH_BASE_SELECTED.send(ctx, self.__sel.base.name, sel=self.__sel)
            return

    def check_auth(self, reaction, player, user):
        if player.active and player.active.is_captain:
            return
        if is_admin(user):
            return
        raise UserLackingPermission

    async def refresh_message(self, *args):
        await display.BASE_SHOW_POOL.edit(self.__msg, sel=self.__sel)
