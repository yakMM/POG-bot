
from display.strings import AllStrings as display
from display.classes import ContextWrapper
from lib.tasks import loop

import modules.config as cfg

from modules.enumerations import MatchStatus, PlayerStatus
from modules.reactions import ReactionHandler, add_handler, rem_handler
from modules.exceptions import UserLackingPermission, AlreadyPicked

import match_process.common as common
from asyncio import sleep

class MapPicking(common.Process, status=MatchStatus.IS_MAPPING):

    def __init__(self, match):
        self.match = match
        self.last_msg = None
        self.picking_captain = None
        self.reaction_handler = ReactionHandler(rem_bot_react = True)
        self.add_callbacks(self.reaction_handler)

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = False
        self.picking_captain = self.match.teams[1].captain

        super().__init__(match, self.picking_captain)


    @common.init_loop
    async def init(self, picker):
        await sleep(0)
        self.match.audio_bot.select_factions()
        await self.set_faction_msg(msg)

