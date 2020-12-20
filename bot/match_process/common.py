
from display import send, SendCtx
from modules.lobby import get_sub, get_all_names_in_lobby
import modules.config as cfg
from lib.tasks import Loop
from asyncio import sleep
import abc
import inspect

from logging import getLogger

log = getLogger("pog_bot")

class PublicFunc:

    @classmethod
    def instanciate(cls, public_fct, base_object):
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
    def instanciate(cls, init_loop, base_object):
        obj = cls(init_loop.loop)
        obj.loop = Loop(coro=obj.loop, count=1)
        obj.base_object = base_object
        return obj

    def __init__(self, func):
        self.loop = func
        self.base_object = None

    def start(self, *args):
        self.loop.start(self.base_object, *args)



def is_public(func):
    return PublicFunc(func)

def init_loop(func):
    return InitLoop(func)


class MetaProcess(type):
    def __new__(cls, c_name, c_base, c_dict, **kwargs):
        obj = type.__new__(cls, c_name, c_base, c_dict)
        return obj

    def __init__(self, c_name, c_base, c_dict, status):
        self.meta_status = status
        self.meta_attributes = list()
        self.meta_init_loop = None
        for func in c_dict.values():
            if isinstance(func, PublicFunc):
                self.meta_attributes.append(func)
            if isinstance(func, InitLoop):
                if self.meta_init_loop:
                    raise ValueError(f"There can be only one init_loop for '{c_name}'")
                self.meta_init_loop = func


class Process(metaclass = MetaProcess, status=None):

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        obj.attributes = dict()
        obj.status = None
        obj.init_loop = None
        for pub_func in obj.meta_attributes:
            obj.attributes[pub_func.name] = PublicFunc.instanciate(pub_func, obj)
            log.debug(f"Instanciating {pub_func.name}!")
        if obj.meta_init_loop:
            obj.init_loop = InitLoop.instanciate(obj.meta_init_loop, obj)
        if obj.meta_status:
            obj.status = obj.meta_status
        return obj

    def __init__(self, match, *args):
        self.match = match
        if self.init_loop:
            self.init_loop.start(*args)
        if self.status:
            self.match.status = self.status




async def get_substitute(match):
    # Get a new player from the lobby, if None available, display
    new_player = get_sub()
    if new_player is None:
        await send("SUB_NO_PLAYER", match.channel)
        return

    # We have a player. Ping them in the lobby and change their status
    Loop(coro=ping_sub_in_lobby, count=1).start(match, new_player)

    new_player.on_match_selected(match.proxy)
    return new_player

async def ping_sub_in_lobby(match, new_player):
    await send("SUB_LOBBY", SendCtx.channel(cfg.channels["lobby"]),\
                            new_player.mention, match.channel.id,\
                            names_in_lobby=get_all_names_in_lobby())


def switch_turn(process, team):
    """ Change the team who can pick.

        Parameters
        ----------
        team : Team
            The team who is currently picking.

        Returns
        -------
        other : Team
            The other team who will pick now
    """
    # Toggle turn
    team.captain.is_turn = False
    
    # Get the other team
    other = process.match.teams[team.id - 1]
    other.captain.is_turn = True
    process.picking_captain = other.captain
    return other