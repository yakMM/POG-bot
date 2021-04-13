from logging import getLogger
from lib.tasks import Loop

log = getLogger("pog_bot")

class PublicFunc:
    def __init__(self, func):
        self.function = func


class InstantiatedPublicFunc:
    def __init__(self, obj, func):
        self.obj = obj
        self.function = func
        self.name = func.__name__

    def __call__(self, *args, **kwargs):
        return self.function(self.obj, *args, **kwargs)


class InitFunc:
    def __init__(self, func):
        self.func = func

    async def __call__(self, obj, *args):
        await self.func(obj, *args)


class MetaProcess(type):
    def __new__(mcs, c_name, c_base, c_dict, **kwargs):
        obj = type.__new__(mcs, c_name, c_base, c_dict)
        return obj

    def __init__(cls, c_name, c_base, c_dict, status):
        super().__init__(cls)
        cls.meta_status = status
        cls.meta_attributes = list()
        cls.meta_init_func = None
        for func in c_dict.values():
            if isinstance(func, PublicFunc):
                cls.meta_attributes.append(func)
            if isinstance(func, InitFunc):
                if cls.meta_init_func:
                    raise ValueError(f"There can be only one init_loop for '{c_name}'")
                cls.meta_init_func = func


class Process(metaclass=MetaProcess, status=None):
    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        obj.attributes = dict()
        obj.status = None
        obj.init_func = None
        for pub_func in obj.meta_attributes:
            log.debug(f"Instantiating {pub_func.function.__name__}!")
            i_func = InstantiatedPublicFunc(obj, pub_func.function)
            obj.attributes[i_func.name] = i_func
            setattr(obj, i_func.name, i_func)
        if obj.meta_init_func:
            obj.init_func = obj.meta_init_func
        if obj.meta_status:
            obj.status = obj.meta_status
        return obj

    def __init__(self, match):
        self.match = match

    def initialize(self):
        Loop(coro=self._async_init, count=1).start()

    def change_status(self, status):
        self.status = status

    async def _async_init(self):
        if self.init_func:
            await self.init_func(self)
        if self.status:
            self.match.status = self.status

    @classmethod
    def public(cls, func):
        return PublicFunc(func)

    @classmethod
    def init_loop(cls, func):
        return InitFunc(func)
