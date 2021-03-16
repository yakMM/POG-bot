from lib.tasks import loop
from asyncio import get_event_loop
from logging import getLogger
from random import randint

from classes.bases import Base

from general.exceptions import ElementNotFound, UserLackingPermission
from general.enumerations import MatchStatus

from display.strings import AllStrings as disp
from display.classes import ContextWrapper

from modules.jaeger_calendar import get_booked_bases
from modules.reactions import ReactionHandler, add_handler, rem_handler
from modules.roles import is_admin

log = getLogger("pog_bot")
MAX_SELECTED = 15


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
        self.__picking_captain = None
        self.__booked = list()
        self.__confirm_msg = None
        self.__nav = BaseNavigator(self, match.channel)
        self._get_booked_from_calendar.start()

    @loop(count=1)
    async def _get_booked_from_calendar(self):
        lp = get_event_loop()
        await lp.run_in_executor(None, get_booked_bases, Base, self.__booked)

    async def clean(self):
        await self.__remove_confirm_msg()
        await self.__nav.remove_msg()

    @property
    def is_booked(self):
        return self.__selected in self.__booked

    def is_base_booked(self, base):
        return base in self.__booked

    @property
    def string_list(self):
        result = list()
        for i in range(len(self.__selection)):
            base = self.__selection[i]
            if self.is_base_booked(base):
                base_string = f"~~{base.name}~~"
            else:
                base_string = f"{base.name}"
            result.append(f"**{str(i + 1)}**: {base_string}")
        return result

    @property
    def current_selection(self):
        return self.__selection

    def get_base_from_selection(self, index):
        return self.__selection[index]

    async def show_base_status(self, ctx):
        if self.__selected is None:
            await disp.BASE_NO_BASE.send(ctx)
        else:
            await disp.BASE_SELECTED.send(ctx, base=self.__selected, is_booked=self.is_booked)

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
            await self.__remove_confirm_msg()
            await disp.BASE_SHOW_LIST.send(ctx, bases_list=self.string_list)
            await self.__nav.reload()

    async def select_by_index(self, ctx, captain, index):
        if 0 <= index < len(self.__selection):
            await self.__select_base(ctx, captain, self.__selection[index])
            return
        await disp.BASE_NOT_FOUND.send(ctx)

    async def confirm_base(self, ctx, captain):
        if not self.__selected:
            await disp.BASE_NO_BASE.send(ctx)
            return
        if not self.__picking_captain:
            await disp.BASE_ALREADY.send(ctx)
            return
        if captain is not self.__picking_captain:
            await disp.BASE_NO_CONFIRM.send(ctx, self.__picking_captain.mention)
            return
        await self.__do_confirm(ctx)

    async def __select_base(self, ctx, picker, base):
        self.__selected = base
        await self.__remove_confirm_msg()
        if is_admin(ctx.author):
            await self.__do_confirm(ctx)
            return
        self.__picking_captain = self.__match.teams[picker.team.id - 1].captain
        await self.__wait_confirm(ctx)
        if self.is_booked:
            await disp.BASE_BOOKED.send(ctx, self.__picking_captain.mention, base.name)

    async def __do_confirm(self, ctx):
        self.__reset_selection()
        self.__picking_captain = None
        self.__match.data.base = self.__selected
        await self.__nav.remove_msg()
        await disp.BASE_ON_SELECT.send(ctx, self.__selected.name, base=self.__selected, is_booked=self.is_booked)
        if self.__match.status is MatchStatus.IS_BASING:
            self.__match.proxy.on_base_found()

    async def __wait_confirm(self, ctx):
        rh = ReactionHandler(rem_bot_react=True)

        @rh.reaction('✅')
        async def reaction_confirm(reaction, player, user):
            if player.active and player.active is self.__picking_captain:
                ctx2 = ContextWrapper.wrap(self.__match.channel)
                ctx2.author = user
                await self.__do_confirm(ctx2)
            else:
                raise UserLackingPermission

        self.__confirm_msg = await disp.BASE_OK_CONFIRM.send(ctx, self.__selected.name, self.__picking_captain.mention)
        add_handler(self.__confirm_msg.id, rh)
        await rh.auto_add_reactions(self.__confirm_msg)

    async def __remove_confirm_msg(self):
        if self.__confirm_msg:
            rem_handler(self.__confirm_msg.id)
            await self.__confirm_msg.clear_reactions()
            self.__confirm_msg = None

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
        self.reaction_handler = ReactionHandler()
        self.reaction_handler.set_reaction("◀️", self.check_auth, self.go_left, self.refresh_message)
        self.reaction_handler.set_reaction("⏺️", self.check_auth, self.select)
        self.reaction_handler.set_reaction("▶️", self.check_auth, self.go_right, self.refresh_message)
        self.reaction_handler.set_reaction("🔀", self.check_auth, self.shuffle, self.refresh_message)
        self.last_msg = None

    @property
    def current_base(self):
        return self.selector.get_base_from_selection(self.index)

    @property
    def is_booked(self):
        return self.selector.is_base_booked(self.current_base)

    async def remove_msg(self):
        if self.last_msg:
            rem_handler(self.last_msg.id)
            await self.last_msg.delete()
            self.last_msg = None

    async def reload(self):
        await self.remove_msg()
        self.length = len(self.selector.current_selection)
        try:
            self.index = randint(0, self.length - 1)
        except ValueError:
            self.index = 0

        msg = await disp.BASE_DISPLAY.send(self.channel, base=self.current_base, is_booked=self.is_booked)
        self.last_msg = msg
        add_handler(msg.id, self.reaction_handler)
        await self.reaction_handler.auto_add_reactions(msg)

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

    async def select(self, reaction, player, user):
        ctx = ContextWrapper.wrap(self.channel)
        ctx.author = user
        await self.selector.select_by_index(ctx, player.active, self.index)
        if self.last_msg:
            await self.last_msg.clear_reactions()

    def check_auth(self, reaction, player, user):
        if player.active and player.active.is_captain:
            return
        if is_admin(user):
            return
        raise UserLackingPermission

    async def refresh_message(self, *args):
        await disp.BASE_DISPLAY.edit(self.last_msg, base=self.current_base, is_booked=self.is_booked)