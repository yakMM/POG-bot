from match import MatchStatus
from display import AllStrings as disp, ContextWrapper
from logging import getLogger

log = getLogger("pog_bot")

picking_states = (MatchStatus.IS_PICKING, MatchStatus.IS_FACTION, MatchStatus.IS_BASING, MatchStatus.IS_WAITING)
captains_ok_states = (MatchStatus.IS_WAITING, MatchStatus.IS_PLAYING, MatchStatus.IS_BASING, MatchStatus.IS_PICKING,
                      MatchStatus.IS_FACTION)


class Command:
    def __init__(self, func, *args):
        self.func = func
        self.status = list()
        self.has_help = None
        self.name = func.__name__
        self.has_status = None
        for arg in args:
            if not isinstance(arg, MatchStatus):
                raise ValueError("Expected MatchStatus")
            self.status.append(arg)

    @classmethod
    def has_help(cls, h_str):
        def decorator(obj):
            obj.has_help = h_str
            return obj
        return decorator

    @classmethod
    def command(cls, *args):
        def decorator(func):
            return cls(func, *args)
        return decorator

    @classmethod
    def has_status(cls, func):
        def decorator(obj):
            obj.has_status = func
            return obj
        return decorator


class InstantiatedCommand:
    def __init__(self, parent, command):
        self.__func = command.func
        self.__status = command.status.copy()
        self.__has_help = command.has_help
        self.__name = command.name
        self.__has_status = command.has_status
        self.__is_running = False
        self.__parent = parent

    @property
    def name(self):
        return self.__name

    def on_team_ready(self, team):
        pass

    def on_clean(self, hard=False):
        pass

    def on_start(self):
        pass

    def on_update(self):
        pass

    def on_status_update(self, status):
        if status in self.__status:
            if not self.__is_running:
                self.on_start()
                self.__is_running = True
            else:
                self.on_update()
        elif status not in self.__status and self.__is_running:
            self.on_clean()
            self.__is_running = False

    def direct_do(self, obj, ctx, *args, **kwargs):
        return self.__func(obj, ctx, *args, **kwargs)

    async def __call__(self, ctx, args=(), **kwargs):
        if self.__has_help:
            if len(args) == 1 and (args[0] == "help" or args[0] == "h"):
                await self.__has_help.send(ctx)
                return
        cmd_name = "unknown"
        try:
            cmd_name = ctx.cmd_name
        except AttributeError:
            try:
                cmd_name = ctx.command.name
            except AttributeError:
                pass
        if self.__parent.match.status is MatchStatus.IS_FREE:
            await disp.MATCH_NO_MATCH.send(ctx, cmd_name)
            return
        if self.__parent.match.status not in self.__status:
            await disp.MATCH_NO_COMMAND.send(ctx, cmd_name)
            return
        if self.__has_status:
            if (len(args) == 0 and not ctx.message.mentions) or (len(args) == 1 and (args[0] == "help" or args[0] == "h")):
                try:
                    await self.__parent.match.get_process_attr(self.__has_status)(ctx)
                    return
                except AttributeError:
                    # This should not happen
                    log.error(f"Attribute error trying to reach '{self.__has_status}' "
                              f"(match status: {self.__parent.match.status})")
        await self.__func(self.__parent, ctx, args, **kwargs)

