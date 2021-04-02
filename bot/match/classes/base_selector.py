from lib.tasks import loop
from asyncio import get_event_loop
from logging import getLogger
from random import randint

from classes.bases import Base

from match.match_status import MatchStatus
from .captain_validator import CaptainValidator

from display import AllStrings as disp, ContextWrapper

from modules.jaeger_calendar import get_booked_bases
import modules.reactions as reactions
from modules.roles import is_admin
import modules.tools as tools


log = getLogger("pog_bot")
MAX_SELECTED = 15

_pog_selected_bases = dict()

last_base = [(None, 0), (None, 0)]


def push_last_bases(base):
    last_base[1] = (last_base[0][0], last_base[0][1])
    last_base[0] = (base, tools.timestamp_now())


def is_last_used(base):
    for i in range(2):
        if base is last_base[i][0]:
            if last_base[i][1] > (tools.timestamp_now() - 14400):
                return True
    return False




class BaseSelector:

    def __init__(self, match, base_pool=False):
        if base_pool:
            self.__all_bases = Base.get_pool()
        else:
            self.__all_bases = Base.get_bases()
        self.__selection = list()
        self.__reset_selection()
        self.__match = match
        self.__selected = None
        self.__booked = list()
        self.__validator = CaptainValidator(self.__match)
        self.add_callbacks(self.__validator)
        self.__nav = BaseNavigator(self, match.channel)
        _pog_selected_bases[self.__match.id] = None
        self._get_booked_from_calendar.start()

    @loop(count=1)
    async def _get_booked_from_calendar(self):
        lp = get_event_loop()
        await lp.run_in_executor(None, get_booked_bases, Base, self.__booked)

    async def clean(self):
        await self.__validator.clean()
        await self.__nav.reaction_handler.destroy()
        _pog_selected_bases[self.__match.id] = None

    def __is_used(self, base):
        for key in _pog_selected_bases.keys():
            if key != self.__match.id:
                if base is _pog_selected_bases[key]:
                    return True
        return False

    @property
    def is_booked(self):
        return self.__selected in self.__booked or self.__is_used(self.__selected)

    def is_base_booked(self, base):
        return base in self.__booked or self.__is_used(base)

    @property
    def string_list(self):
        result = list()
        for i in range(len(self.__selection)):
            base = self.__selection[i]
            if self.is_base_booked(base):
                base_string = f"~~{base.name}~~"
            else:
                base_string = f"{base.name}"
            last_used = ""
            if is_last_used(base):
                last_used = " **(last played)**"
            result.append(f"**{str(i + 1)}**: {base_string}{last_used}")
        return result

    @property
    def current_selection(self):
        return self.__selection

    def get_base_from_selection(self, index):
        return self.__selection[index]

    def add_callbacks(self, validator):
        @validator.confirm
        async def do_confirm(ctx):
            self.__reset_selection()
            _pog_selected_bases[self.__match.id] = self.__selected
            self.__match.data.base = self.__selected
            await self.__nav.reaction_handler.destroy()
            await disp.BASE_ON_SELECT.send(ctx, self.__selected.name, base=self.__selected, is_booked=self.is_booked)
            if self.__match.status is MatchStatus.IS_BASING:
                await self.__match.proxy.on_base_found()

    async def show_base_status(self, ctx):
        if self.__selected is None:
            if self.__match.status is MatchStatus.IS_BASING:
                await disp.BASE_NO_BASE_WAITING.send(ctx)
            else:
                await disp.BASE_NO_BASE.send(ctx)
        else:
            await disp.BASE_SELECTED.send(ctx, base=self.__selected, is_booked=self.is_booked)

    async def process_request(self, ctx, a_player, args):
        if a_player:
            if await self.__validator.check_message(ctx, a_player, args):
                return

        if len(args) == 0:
            # If no arg in the command
            await self.display_all(ctx)
            return
        if len(args) == 1:
            if args[0] == "list" or args[0] == "l":
                await self.display_all(ctx, force=True)
                return
            if args[0].isnumeric():
                # If arg is a number
                await self.select_by_index(ctx, a_player, int(args[0]) - 1)
                return

        # If any other arg (expecting base name)
        await self.select_by_name(ctx, a_player, args)

    async def display_all(self, ctx, force=False, mentions=None):
        if self.__selected and not force:
            await self.show_base_status(ctx)
            return
        if not mentions:
            mentions = ctx.author.mention
        await disp.BASE_CALENDAR.send(ctx, mentions)
        if self.__selection:
            await disp.BASE_SHOW_LIST.send(ctx, bases_list=self.string_list)
            await self.__nav.reload()

    async def select_by_name(self, ctx, picker, args):
        arg = " ".join(args)
        current_list = Base.get_bases_from_name(arg, base_pool=True)
        if len(current_list) == 0:
            await disp.BASE_NOT_FOUND.send(ctx)
        elif len(current_list) == 1:
            await self.__select_base(ctx, picker, current_list[0])
        elif len(current_list) > MAX_SELECTED:
            await disp.BASE_TOO_MUCH.send(ctx)
        else:
            self.__selection = current_list
            await self.__validator.clean()
            await disp.BASE_SHOW_LIST.send(ctx, bases_list=self.string_list)
            await self.__nav.reload()

    async def select_by_index(self, ctx, captain, index):
        if 0 <= index < len(self.__selection):
            await self.__select_base(ctx, captain, self.__selection[index])
            return
        await disp.BASE_NOT_FOUND.send(ctx)

    async def __select_base(self, ctx, picker, base):
        self.__selected = base
        if is_admin(ctx.author):
            await self.__validator.force_confirm(ctx)
            return
        other_captain = self.__match.teams[picker.team.id - 1].captain
        msg = await disp.BASE_OK_CONFIRM.send(ctx, self.__selected.name, other_captain.mention)
        await self.__validator.wait_valid(picker, msg)
        if self.is_booked:
            await disp.BASE_BOOKED.send(ctx, other_captain.mention, base.name)

    def __reset_selection(self):
        if len(self.__all_bases) <= MAX_SELECTED:
            self.__selection = self.__all_bases.copy()
        else:
            self.__selection.clear()


class BaseNavigator:
    def __init__(self, sel, match_channel):
        self.selector = sel
        self.channel = match_channel
        self.index = 0
        self.length = 0
        self.reaction_handler = reactions.SingleMessageReactionHandler(remove_msg=True)
        self.reaction_handler.set_reaction("◀️", self.check_auth, self.go_left, self.refresh_message)
        self.reaction_handler.set_reaction("⏺️", self.check_auth, self.select)
        self.reaction_handler.set_reaction("▶️", self.check_auth, self.go_right, self.refresh_message)
        self.reaction_handler.set_reaction("🔀", self.check_auth, self.shuffle, self.refresh_message)

    @property
    def current_base(self):
        return self.selector.get_base_from_selection(self.index)

    @property
    def is_booked(self):
        return self.selector.is_base_booked(self.current_base)

    async def reload(self):
        self.length = len(self.selector.current_selection)
        try:
            self.index = randint(0, self.length - 1)
        except ValueError:
            self.index = 0

        msg = await disp.BASE_DISPLAY.send(self.channel, base=self.current_base, is_booked=self.is_booked)
        await self.reaction_handler.set_new_msg(msg)

    def go_right(self, *args):
        self.index += 1
        self.index %= self.length

    def go_left(self, *args):
        self.index -= 1
        self.index %= self.length

    def shuffle(self, *args):
        # Get a new base at random
        old_index = self.index
        # Exclude the last base
        self.index = randint(0, self.length - 2)
        # So that if we get the old base, we take the last base instead
        if self.index == old_index:
            self.index = self.length - 1
        # Like so, the odds are even for all bases

    async def select(self, reaction, player, user, msg):
        ctx = ContextWrapper.wrap(self.channel)
        ctx.author = user
        await self.selector.select_by_index(ctx, player.active, self.index)
        await self.reaction_handler.clear_reactions()

    def check_auth(self, reaction, player, user, msg):
        if player.active and player.active.is_captain:
            return
        if is_admin(user):
            return
        raise reactions.UserLackingPermission

    async def refresh_message(self, *args):
        await disp.BASE_DISPLAY.edit(self.reaction_handler.msg, base=self.current_base, is_booked=self.is_booked)
