from lib.tasks import loop
from asyncio import get_event_loop
from logging import getLogger

from classes.bases import Base

from display.strings import AllStrings as disp
from display.classes import ContextWrapper

from modules.jaeger_calendar import get_booked_bases

log = getLogger("pog_bot")
MAX_SELECTED = 15


class BaseSelector:

    def __init__(self, match, base_pool=False):
        if base_pool:
            self.__all_bases = Base.get_pool()
            if len(self.__all_bases) <= MAX_SELECTED:
                self.__selection = Base.get_pool()
        else:
            self.__all_bases = Base.get_bases()
            self.__selection = list()
        self.__match = match
        self.__selected = Base.get_bases_from_name("Acan south")[0]
        self.__booked = list()
        self._get_booked_from_calendar.start()

    @loop(count=1)
    async def _get_booked_from_calendar(self):
        lp = get_event_loop()
        await lp.run_in_executor(None, get_booked_bases, Base, self.__booked)

    @property
    def is_booked(self):
        return self.__selected in self.__booked

    async def show_base_status(self, ctx):
        if self.__selected is None:
            await disp.BASE_NO_SELECTED.send(ctx)
        else:
            await disp.BASE_SELECTED.send(ctx, base=self.__selected, is_booked=self.is_booked)

    async def on_base_command(self, ctx, args):
