from inspect import iscoroutinefunction as is_coroutine
from discord.errors import NotFound
from logging import getLogger

from lib.tasks import loop, Loop

from modules.message_filter import is_spam, unlock

import asyncio

_all_handlers = dict()

_client = None

log = getLogger("pog_bot")


def init(client):
    global _client
    _client = client

class UserLackingPermission(Exception):
    pass


async def reaction_handler(reaction, user, player):
    msg = reaction.message
    if await is_spam(user, msg.channel):
        return
    handler = _all_handlers.get(msg.id)
    log.debug(f"Handler dict size: {len(_all_handlers)}")
    if handler is None:
        return
    await handler.run(reaction, player, user, msg)
    unlock(user.id)


def add_handler(m_id, handler):
    _all_handlers[m_id] = handler


_locked_msg = list()


def _lock_msg(msg):
    if msg.id not in _locked_msg:
        _locked_msg.append(msg.id)


def _unlock_msg(msg):
    if msg.id in _locked_msg:
        _locked_msg.remove(msg.id)


def rem_handler(m_id):
    try:
        del _all_handlers[m_id]
    except KeyError:
        pass


def auto_clear(msg):
    if msg:
        _lock_msg(msg)
        Loop(coro=clear_loop, count=1).start(msg)


async def clear_loop(msg):
    await msg.clear_reactions()
    rem_handler(msg.id)
    _unlock_msg(msg)


class ReactionHandler:
    def __init__(self, rem_user_react=True, rem_bot_react=False, auto_destroy=False):
        self.__f_dict = dict()
        self.__rem_user_react = rem_user_react
        self.__rem_bot_react = rem_bot_react
        self.__auto_destroy = auto_destroy

    # TODO: DEBUG
    def print(self):
        print(self.__f_dict)

    @property
    def _string(self):
        return str(self.__f_dict)

    def is_reaction(self, react):
        return str(react.emoji) in self.__f_dict

    def set_reaction(self, react, *fcts):
        self.__f_dict[react] = [fct for fct in fcts]

    def add_reaction(self, react, fct):
        if react not in self.__f_dict:
            self.__f_dict[react] = list()
        self.__f_dict[react].append(fct)

    def rem_reaction(self, react):
        react = str(react)
        if react in self.__f_dict:
            del self.__f_dict[react]

    async def run(self, reaction, player, user, msg):
        try:
            if msg.id in _locked_msg:
                raise UserLackingPermission
            _lock_msg(msg)
            funcs = self.__f_dict[str(reaction.emoji)]
            for func in funcs:
                if is_coroutine(func):
                    await func(reaction, player, user, msg)
                else:
                    func(reaction, player, user, msg)
        except (KeyError, UserLackingPermission):
            _unlock_msg(msg)
        else:
            if msg.id in _all_handlers:
                if self.__auto_destroy:
                    _lock_msg(msg)
                    await msg.clear_reactions()
                    rem_handler(msg.id)
                    _unlock_msg(msg)
                    return
                if self.__rem_bot_react:
                    _lock_msg(msg)
                    await msg.remove_reaction(reaction.emoji, _client.user)
                    if self.__rem_user_react:
                        await msg.remove_reaction(reaction.emoji, user)
                    rem_handler(msg.id)
                    _unlock_msg(msg)
                    return
            _unlock_msg(msg)
        if msg.id in _all_handlers and self.__rem_user_react:
            await msg.remove_reaction(reaction.emoji, user)

    async def _auto_add_reactions(self, msg):
        _lock_msg(msg)
        for react in self.__f_dict.keys():
            await msg.add_reaction(react)
        _unlock_msg(msg)

    async def auto_remove_reactions(self, msg):
        _lock_msg(msg)
        for react in self.__f_dict.keys():
            await msg.remove_reaction(react, _client.user)
        _unlock_msg(msg)

    async def auto_add(self, msg):
        _lock_msg(msg)
        add_handler(msg.id, self)
        await self._auto_add_reactions(msg)

    def reaction(self, *args):
        def decorator(func):
            for react in args:
                self.add_reaction(react, func)
            return func
        return decorator



class SingleMessageReactionHandler(ReactionHandler):
    def __init__(self, remove_msg=False, **kwargs):
        super().__init__(**kwargs)
        self.remove_msg = remove_msg
        self.__msg = None

    @property
    def is_msg(self):
        return self.__msg is not None

    @property
    def msg(self):
        return self.__msg

    def is_locked(self):
        if not self.__msg:
            return True
        if self.__msg in _locked_msg:
            return True
        return False

    def lock(self):
        if self.__msg:
            _lock_msg(self.__msg)

    def unlock(self):
        if self.__msg:
            _unlock_msg(self.__msg)

    def clear(self):
        if not self.__msg:
            return
        _lock_msg(self.__msg)
        if self.remove_msg:
            rem_handler(self.__msg.id)
        Loop(coro=self._destroy, count=1).start(self.__msg)
        self.__msg = None

    async def _destroy(self, msg):
        if self.remove_msg:
            await msg.delete()
        else:
            await msg.clear_reactions()
            rem_handler(msg.id)
        _unlock_msg(msg)

    async def set_new_msg(self, new_msg):
        self.clear()
        _lock_msg(new_msg)
        add_handler(new_msg.id, self)
        await super()._auto_add_reactions(new_msg)
        self.__msg = new_msg
        # _unlock_msg will be done in auto_add_reactions

