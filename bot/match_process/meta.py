from logging import getLogger
from lib.tasks import Loop

log = getLogger("pog_bot")


class PublicFunc:

    @classmethod
    def instantiate(cls, public_fct, base_object):
        obj = cls(public_fct.function)
        obj.base_object = base_object
        return obj

    def __init__(self, func):
        self.function = func
        self.name = func.__name__
        self.base_object = None

    def __call__(self, *args, **kwargs):
        return self.function(self.base_object, *args, **kwargs)


class InitLoop:

    @classmethod
    def instantiate(cls, init_loop, base_object):
        obj = cls(init_loop.loop)
        obj.loop = Loop(coro=obj.loop, count=1)
        obj.base_object = base_object
        return obj

    def __init__(self, func):
        self.loop = func
        self.base_object = None

    def start(self, *args):
        self.loop.start(self.base_object, *args)


def public(func):
    return PublicFunc(func)


def init_loop(func):
    return InitLoop(func)


class MetaProcess(type):
    def __new__(mcs, c_name, c_base, c_dict, **kwargs):
        obj = type.__new__(mcs, c_name, c_base, c_dict)
        return obj

    def __init__(cls, c_name, c_base, c_dict, status):
        cls.meta_status = status
        cls.meta_attributes = list()
        cls.meta_init_loop = None
        for func in c_dict.values():
            if isinstance(func, PublicFunc):
                cls.meta_attributes.append(func)
            if isinstance(func, InitLoop):
                if cls.meta_init_loop:
                    raise ValueError(f"There can be only one init_loop for '{c_name}'")
                cls.meta_init_loop = func


class Process(metaclass=MetaProcess, status=None):

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        obj.attributes = dict()
        obj.status = None
        obj.init_loop = None
        for pub_func in obj.meta_attributes:
            obj.attributes[pub_func.name] = PublicFunc.instantiate(pub_func, obj)
            log.debug(f"Instanciating {pub_func.name}!")
        if obj.meta_init_loop:
            obj.init_loop = InitLoop.instantiate(obj.meta_init_loop, obj)
        if obj.meta_status:
            obj.status = obj.meta_status
        return obj

    def __init__(self, match, *args):
        self.match = match
        if self.init_loop:
            self.init_loop.start(*args)
        if self.status:
            self.match.status = self.status
