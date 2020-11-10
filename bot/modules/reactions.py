from modules.enumerations import PlayerStatus
from modules.exceptions import ElementNotFound, UserLackingPermission
from inspect import iscoroutinefunction as is_coroutine

_allHandlers = dict()

_client = None

def init(client):
    global _client
    _client = client


async def reaction_handler(reaction, user, player):
    msg = reaction.message
    handler = _allHandlers.get(msg.id)
    if handler is None:
        return
    await handler.run(reaction, player)
    if handler.rem_user_react:
        await msg.remove_reaction(reaction.emoji, user)
    if handler.rem_bot_react:
        await msg.remove_reaction(reaction.emoji, _client.user)
        rem_handler(msg.id)

def add_handler(m_id, handler):
    _allHandlers[m_id] = handler

def rem_handler(m_id):
    try:
        del _allHandlers[m_id]
    except KeyError:
        pass

class ReactionHandler:
    def __init__(self, rem_user_react = True, rem_bot_react = False):
        self.__fDict = dict()
        self.__remUserReact = rem_user_react
        self.__remBotReact = rem_bot_react
    
    @property
    def rem_user_react(self):
        return self.__remUserReact

    @property
    def rem_bot_react(self):
        return self.__remBotReact

    def set_reaction(self, react, *fcts):
        self.__fDict[react] = [fct for fct in fcts]

    async def run(self, reaction, player):
        try:
            fcts = self.__fDict[str(reaction.emoji)]
        except KeyError:
            return
        try:
            for fct in fcts:
                if is_coroutine(fct):
                    await fct(reaction, player)
                else:
                    fct(reaction, player)
        except UserLackingPermission:
            return
    
    async def auto_add_reactions(self, msg):
        for react in self.__fDict.keys():
            await msg.add_reaction(react)

    async def auto_remove_reactions(self, msg):
        for m_react in msg.reactions:
            if str(m_react) in self.__fDict.keys() and m_react.me:
                await msg.remove_reaction(m_react, _client.user)






# if reaction.message.author.bot and not user.bot and reaction.message.channel.id in cfg.channels["matches"]:
#             cleaned_reaction_message = re.sub("<.+?>", "", reaction.message.content)
#             emoji_obj = Emoji()
#             current_match = get_match(reaction.message.channel.id)

#             # todo: WIP -- below is for team selection -- should be moved out of main.py to the correct module @yak
#             # if current_match.status == MatchStatus.IS_PICKING:
#             #     if user.id in [tm.captain.id for tm in current_match.teams]:
#             #         if cleaned_reaction_message in clean_string_enum(_StringEnum.MATCH_SHOW_PICKS):
#             #             value = -1
#             #             if reaction.emoji in emoji_obj.numeric:
#             #                 value = emoji_obj.numeric.index(reaction.emoji)
#             #
#             #             await reaction.remove(user)
#             #
#             #             if 0 <= value <= 9:
#             #                 await edit("MATCH_SHOW_PICKS", current_match.id, current_match.teams[0].captain.mention, match=current_match)
#             #                 # could also be PK_OK or PK_OK_2

#             # todo: below is for map selection -- should be moved out of main.py to the correct module @yak
#             if current_match.status == MatchStatus.IS_MAPPING:
#                 if cleaned_reaction_message in clean_string_enum(_StringEnum.PK_SHOW_REACT_MAP) or \
#                         cleaned_reaction_message in clean_string_enum(_StringEnum.PK_WAIT_MAP):
#                     value = -1
#                     if reaction.emoji in emoji_obj.escape:
#                         value = 27  # using the keycode value for escape but really it can be anything unique
#                     elif reaction.emoji in emoji_obj.numeric:
#                         value = emoji_obj.numeric.index(reaction.emoji)

#                     await reaction.remove(user)

#                     if 1 <= value <= len(current_match.map_selector.get_selection()):
#                         await edit("PK_SHOW_REACT_MAP", reaction.message, map=current_match.map_selector.get_selection()[value - 1])
#                     elif value == 27:
#                         captain_pings = [tm.captain.mention for tm in current_match.teams]
#                         await edit("PK_WAIT_MAP", reaction.message, sel=current_match.map_selector, *captain_pings)
# ⏺️
# ▶️
# ◀️