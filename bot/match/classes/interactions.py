from modules.interactions import InteractionHandler, InteractionInvalid, InteractionNotAllowed
from match.common import get_check_player, get_check_captain
from display import InteractionContext
from match import MatchStatus


class CaptainInteractionHandler(InteractionHandler):
    def __init__(self, match, view, check_turn=True, **kwargs):
        self.match = match
        self.check_turn = check_turn
        super().__init__(match.proxy, view, **kwargs)

    async def run_player_check(self, interaction):
        if self.match.status is MatchStatus.IS_RUNNING:
            raise InteractionInvalid("Match is running!")
        i_ctx = InteractionContext(interaction)
        captain = await get_check_captain(i_ctx, self.match, check_turn=self.check_turn)
        if not captain:
            raise InteractionNotAllowed
        return captain


class PlayerInteractionHandler(InteractionHandler):
    def __init__(self, match, view, **kwargs):
        self.match = match
        super().__init__(match.proxy, view, **kwargs)

    async def run_player_check(self, interaction):
        if self.match.status is MatchStatus.IS_RUNNING:
            raise InteractionInvalid("Match is running!")
        i_ctx = InteractionContext(interaction)
        player = await get_check_player(i_ctx, self.match)
        if not player:
            raise InteractionNotAllowed
        return player
