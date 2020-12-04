from modules.enumerations import PlayerStatus
from modules.exceptions import ElementNotFound, UserLackingPermission
from inspect import iscoroutinefunction as is_coroutine

_all_handlers = dict()

_client = None

def init(client):
    global _client
    _client = client


async def reaction_handler(reaction, user, player):
    msg = reaction.message
    handler = _all_handlers.get(msg.id)
    if handler is None:
        return
    try:
        result = await handler.run(reaction, player, user)
        if result and handler.rem_bot_react:
            await msg.remove_reaction(reaction.emoji, _client.user)
            rem_handler(msg.id)
    except UserLackingPermission:
        pass
    if handler.rem_user_react:
        await msg.remove_reaction(reaction.emoji, user)


def add_handler(m_id, handler):
    _all_handlers[m_id] = handler

def rem_handler(m_id):
    try:
        del _all_handlers[m_id]
    except KeyError:
        pass

class ReactionHandler:
    def __init__(self, rem_user_react = True, rem_bot_react = False):
        self.__f_dict = dict()
        self.__rem_user_react = rem_user_react
        self.__rem_bot_react = rem_bot_react
    
    @property
    def rem_user_react(self):
        return self.__rem_user_react

    @property
    def rem_bot_react(self):
        return self.__rem_bot_react

    def is_reaction(self, react):
        return str(react.emoji) in self.__f_dict

    def set_reaction(self, react, *fcts):
        self.__f_dict[react] = [fct for fct in fcts]

    async def run(self, reaction, player, user):
        try:
            fcts = self.__f_dict[str(reaction.emoji)]
        except KeyError:
            return False
        for fct in fcts:
            if is_coroutine(fct):
                await fct(reaction, player, user)
            else:
                fct(reaction, player, user)
        return True

    async def auto_add_reactions(self, msg):
        for react in self.__f_dict.keys():
            await msg.add_reaction(react)

    async def auto_remove_reactions(self, msg):
        for m_react in msg.reactions:
            if str(m_react) in self.__f_dict.keys() and m_react.me:
                await msg.remove_reaction(m_react, _client.user)
