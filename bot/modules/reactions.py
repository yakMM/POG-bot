from inspect import iscoroutinefunction as is_coroutine
from discord.errors import NotFound
from logging import getLogger

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
    handler = _all_handlers.get(msg.id)
    log.debug(f"Handler dict size: {len(_all_handlers)}")
    if handler is None:
        return
    await handler.run(reaction, player, user, msg)


def add_handler(m_id, handler):
    _all_handlers[m_id] = handler


def rem_handler(m_id):
    try:
        del _all_handlers[m_id]
    except KeyError:
        pass


class ReactionHandler:
    def __init__(self, rem_user_react=True, rem_bot_react=False, auto_destroy=False):
        self.__f_dict = dict()
        self.__rem_user_react = rem_user_react
        self.__rem_bot_react = rem_bot_react
        self.__auto_destroy = auto_destroy
        self.lock = False

    # TODO: DEBUG
    def print(self):
        print(self.__f_dict)


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
            if self.lock:
                raise UserLackingPermission
            funcs = self.__f_dict[str(reaction.emoji)]
            for func in funcs:
                if is_coroutine(func):
                    await func(reaction, player, user, msg)
                else:
                    func(reaction, player, user, msg)
        except (KeyError, UserLackingPermission):
            pass
        else:
            if self.__auto_destroy:
                rem_handler(msg.id)
                await msg.clear_reactions()
                return
            if self.__rem_bot_react:
                rem_handler(msg.id)
                await msg.remove_reaction(reaction.emoji, _client.user)
        if self.__rem_user_react:
            await msg.remove_reaction(reaction.emoji, user)

    async def auto_add_reactions(self, msg):
        self.lock = True
        for react in self.__f_dict.keys():
            await msg.add_reaction(react)
        self.lock = False

    async def auto_remove_reactions(self, msg):
        self.lock = True
        for react in self.__f_dict.keys():
            await msg.remove_reaction(react, _client.user)
        self.lock = False

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

    async def clear_reactions(self):
        if self.__msg:
            await self.__msg.clear_reactions()

    async def destroy(self):
        if self.__msg:
            rem_handler(self.__msg.id)
            if self.remove_msg:
                await self.msg.delete()
            else:
                await self.__msg.clear_reactions()
            self.__msg = None

    async def set_new_msg(self, new_msg):
        await self.destroy()
        self.__msg = new_msg
        add_handler(self.__msg.id, self)
        await super().auto_add_reactions(self.__msg)


