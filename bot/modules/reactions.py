from modules.enumerations import PlayerStatus
from modules.display import edit
from modules.exceptions import ElementNotFound, UserLackingPermission
from lib import tasks
from inspect import iscoroutinefunction as isCoroutine

_allHandlers = dict()

_client = None

def init(client):
    global _client
    _client = client


async def reactionHandler(reaction, user, player):
    msg = reaction.message
    handler = _allHandlers.get(msg.id)
    if handler is None:
        return
    await handler.run(reaction, player)
    if handler.remUserReact:
        await msg.remove_reaction(reaction.emoji, user)
    if handler.remBotReact:
        await msg.remove_reaction(reaction.emoji, _client.user)
        remHandler(msg.id)

def addHandler(mId, handler):
    _allHandlers[mId] = handler

def remHandler(mId):
    try:
        del _allHandlers[mId]
    except KeyError:
        pass

class ReactionHandler:
    def __init__(self, remUserReact = True, remBotReact = False):
        self.__fDict = dict()
        self.__remUserReact = remUserReact
        self.__remBotReact = remBotReact
    
    @property
    def remUserReact(self):
        return self.__remUserReact

    @property
    def remBotReact(self):
        return self.__remBotReact

    def setReaction(self, react, *fcts):
        self.__fDict[react] = [fct for fct in fcts]

    async def run(self, reaction, player):
        try:
            fcts = self.__fDict[str(reaction.emoji)]
        except KeyError:
            return
        try:
            for fct in fcts:
                if isCoroutine(fct):
                    await fct(reaction, player)
                else:
                    fct(reaction, player)
        except UserLackingPermission:
            return
    
    async def autoAddReactions(self, msg):
        for react in self.__fDict.keys():
            await msg.add_reaction(react)






# if reaction.message.author.bot and not user.bot and reaction.message.channel.id in cfg.channels["matches"]:
#             cleaned_reaction_message = re.sub("<.+?>", "", reaction.message.content)
#             emoji_obj = Emoji()
#             currentMatch = getMatch(reaction.message.channel.id)

#             # todo: WIP -- below is for team selection -- should be moved out of main.py to the correct module @yak
#             # if currentMatch.status == MatchStatus.IS_PICKING:
#             #     if user.id in [tm.captain.id for tm in currentMatch.teams]:
#             #         if cleaned_reaction_message in cleanStringEnum(_StringEnum.MATCH_SHOW_PICKS):
#             #             value = -1
#             #             if reaction.emoji in emoji_obj.numeric:
#             #                 value = emoji_obj.numeric.index(reaction.emoji)
#             #
#             #             await reaction.remove(user)
#             #
#             #             if 0 <= value <= 9:
#             #                 await edit("MATCH_SHOW_PICKS", currentMatch.id, currentMatch.teams[0].captain.mention, match=currentMatch)
#             #                 # could also be PK_OK or PK_OK_2

#             # todo: below is for map selection -- should be moved out of main.py to the correct module @yak
#             if currentMatch.status == MatchStatus.IS_MAPPING:
#                 if cleaned_reaction_message in cleanStringEnum(_StringEnum.PK_SHOW_REACT_MAP) or \
#                         cleaned_reaction_message in cleanStringEnum(_StringEnum.PK_WAIT_MAP):
#                     value = -1
#                     if reaction.emoji in emoji_obj.escape:
#                         value = 27  # using the keycode value for escape but really it can be anything unique
#                     elif reaction.emoji in emoji_obj.numeric:
#                         value = emoji_obj.numeric.index(reaction.emoji)

#                     await reaction.remove(user)

#                     if 1 <= value <= len(currentMatch.mapSelector.getSelection()):
#                         await edit("PK_SHOW_REACT_MAP", reaction.message, map=currentMatch.mapSelector.getSelection()[value - 1])
#                     elif value == 27:
#                         captainPings = [tm.captain.mention for tm in currentMatch.teams]
#                         await edit("PK_WAIT_MAP", reaction.message, sel=currentMatch.mapSelector, *captainPings)
# ⏺️
# ▶️
# ◀️