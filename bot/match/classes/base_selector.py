from lib.tasks import loop
from asyncio import get_event_loop
from logging import getLogger
from modules.interactions import InteractionHandler, InteractionNotAllowed, InteractionInvalid

from classes.bases import Base

from match.match_status import MatchStatus
from .captain_validator import CaptainValidator

from display import AllStrings as disp, ContextWrapper, InteractionContext

from modules.jaeger_calendar import get_booked_bases
from modules.roles import is_admin
import modules.tools as tools

from match.common import get_check_captain


log = getLogger("pog_bot")
MAX_SELECTED = 15

_pog_selected_bases = dict()

last_base = [(None, 0), (None, 0)]


def push_last_bases(base):
    last_base[1] = (last_base[0][0], last_base[0][1])
    last_base[0] = (base.id, tools.timestamp_now())


def is_last_used(base):
    for i in range(2):
        if base.id == last_base[i][0]:
            if last_base[i][1] > (tools.timestamp_now() - 14400):
                return True
    return False


def on_match_over(m_id):
    if m_id in _pog_selected_bases:
        del _pog_selected_bases[m_id]


class BaseSelector:

    def __init__(self, match, base_pool=False):
        if base_pool:
            self.__all_bases = Base.get_pool()
        else:
            self.__all_bases = Base.get_bases()
        self.__was_selection_modified = True
        self.__selection = list()
        self.__match = match
        self.__selected = None
        self.__booked = list()
        self.__reset_selection()
        self.__validator = CaptainValidator(self.__match)
        self.__base_interaction = InteractionHandler(disable_after_use=False)
        self.__add_callbacks(self.__validator, self.__base_interaction)
        self._get_booked_from_calendar.start()

    @loop(count=1)
    async def _get_booked_from_calendar(self):
        lp = get_event_loop()
        await lp.run_in_executor(None, get_booked_bases, Base, self.__booked)

    def clean(self):
        self.__validator.clean()
        self.__base_interaction.clean()

    def __is_used(self, base):
        for key in _pog_selected_bases.keys():
            if key != self.__match.id:
                if base.id == _pog_selected_bases[key]:
                    return True
        return False

    @property
    def is_booked(self):
        return self.__selected in self.__booked or self.__is_used(self.__selected)

    def is_base_booked(self, base):
        return base in self.__booked or self.__is_used(base)

    @property
    def bases_list(self):
        result = list()
        for base in self.__selection:
            result.append(
                {'name': base.name,
                 'id': base.id,
                 'is_booked': self.is_base_booked(base),
                 'was_played_recently': is_last_used(base)
                 })
        return result

    def __add_callbacks(self, validator, interaction_handler):
        @validator.confirm
        async def do_confirm(ctx, base):
            self.__reset_selection()
            self.__selected = base
            _pog_selected_bases[self.__match.id] = base.id
            self.__match.data.base = base
            self.__base_interaction.clean()
            await disp.BASE_ON_SELECT.send(ctx, base.name, base=base, is_booked=self.is_booked)
            if self.__match.status is MatchStatus.IS_BASING:
                self.__match.proxy.on_base_found()
            self.__match.plugin_manager.on_base_selected(base)

        @interaction_handler.callback('base_selector')
        async def base_select(player, interaction_id, interaction, values):
            author = interaction.user
            captain = None
            if not is_admin(author):
                i_ctx = InteractionContext(interaction)
                captain, msg = get_check_captain(i_ctx, self.__match, check_turn=False)
                if msg:
                    await msg
                    raise InteractionNotAllowed
            ctx = ContextWrapper.wrap(self.__match.channel, author=author)
            try:
                value = int(values[0])
            except (ValueError, IndexError):
                raise InteractionInvalid("invalid value!")
            base = self.find_by_id(value)
            if not base:
                raise InteractionInvalid("unknown base!")
            await self.__select_base(ctx, captain, base)

    async def show_base_status(self, ctx):
        if self.__selected is None:
            if self.__match.status is MatchStatus.IS_BASING:
                await disp.BASE_NO_BASE_WAITING.send(ctx)
            else:
                await disp.BASE_NO_BASE.send(ctx)
        else:
            await disp.BASE_SELECTED.send(ctx, self.__selected.name, base=self.__selected, is_booked=self.is_booked)

    async def process_request(self, ctx, captain, args):
        if len(args) == 0:
            # If no arg in the command
            await self.display_all(ctx)
            return
        if len(args) == 1:
            if args[0] == "list" or args[0] == "l":
                await self.display_all(ctx, force=True)
                return

        # If any other arg (expecting a base name)
        await self.select_by_name(ctx, captain, args)

    async def display_all(self, ctx, force=False, mentions=None):
        if self.__selected and not force:
            await self.show_base_status(ctx)
            return
        self.__reset_selection()
        if not mentions:
            mentions = ctx.author.mention
        await disp.BASE_CALENDAR.send(ctx, mentions)
        if self.__selection:
            ctx = self.__base_interaction.get_new_context(ctx)
            await disp.BASE_SHOW_LIST.send(ctx, bases_list=self.bases_list)

    def find_by_id(self, base_id):
        for base in self.__selection:
            if base.id == base_id:
                return base

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
            self.__was_selection_modified = True
            self.__validator.clean()
            ctx = self.__base_interaction.get_new_context(ctx)
            await disp.BASE_SHOW_LIST.send(ctx, bases_list=self.bases_list)

    async def __select_base(self, ctx, picker, base):
        if is_admin(ctx.author):
            await self.__validator.force_confirm(ctx, base=base)
            return
        other_captain = self.__match.teams[picker.team.id - 1].captain
        ctx = self.__validator.arm(ctx, picker, base=base)
        await disp.BASE_OK_CONFIRM.send(ctx, base.name, other_captain.mention)
        if self.is_base_booked(base):
            await disp.BASE_BOOKED.send(ctx, other_captain.mention, base.name)

    def __reset_selection(self):
        if self.__was_selection_modified:
            self.__was_selection_modified = False
            if len(self.__all_bases) <= MAX_SELECTED:
                self.__selection = self.__all_bases.copy()
            else:
                self.__selection.clear()
