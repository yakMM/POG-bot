from general.enumerations import MatchStatus
from modules.reactions import ReactionHandler

import match_process.meta as meta
from asyncio import sleep

class MapPicking(meta.Process, status=MatchStatus.IS_BASING):

    def __init__(self, match):
        self.match = match
        self.last_msg = None
        self.picking_captain = None
        self.reaction_handler = ReactionHandler(rem_bot_react = True)

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = False
        self.picking_captain = self.match.teams[1].captain

        super().__init__(match, self.picking_captain)


    @meta.init_loop
    async def init(self, picker):
        await sleep(0)

