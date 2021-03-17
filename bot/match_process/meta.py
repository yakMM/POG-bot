from logging import getLogger
from lib.tasks import Loop

log = getLogger("pog_bot")


class PublicFunc:
    def __init__(self, func):
        self.function = func
        self.name = func.__name__
        self.base_object = None

    def instantiate(self, base_object):
        self.base_object = base_object

    def __call__(self, *args, **kwargs):
        return self.function(self.base_object, *args, **kwargs)


class InitFunc:
    def __init__(self, func):
        self.func = func
        self.base_object = None

    def instantiate(self, base_object):
        self.base_object = base_object

    async def __call__(self, *args):
        await self.func(self.base_object, *args)


def public(func):
    return PublicFunc(func)

def init_loop(func):
    return InitFunc(func)


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
            log.debug(f"Instanciating {pub_func.name}!")
            pub_func.instantiate(obj)
            obj.attributes[pub_func.name] = pub_func
        if obj.meta_init_func:
            obj.meta_init_func.instantiate(obj)
            obj.init_func = obj.meta_init_func
        if obj.meta_status:
            obj.status = obj.meta_status
        return obj

    def __init__(self, match, *args):
        self.match = match
        Loop(coro=self._async_init, count=1).start(*args)

    async def _async_init(self, *args):
        if self.init_func:
            await self.init_func(*args)
        if self.status:
            self.match.status = self.status
