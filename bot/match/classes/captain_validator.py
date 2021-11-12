import modules.reactions as reactions
import modules.interactions as interactions
from modules.tools import UnexpectedError

from display import AllStrings as disp, ContextWrapper, InteractionContext, views
from match import MatchStatus
from classes import Player
import modules.config as cfg
from match.common import get_check_captain


class CaptainValidator:
    def __init__(self, match):
        self.ih = interactions.InteractionHandler(match, views.validation_buttons, disable_after_use=True)
        self.match = match
        self.expected = None
        self.kwargs = dict()
        self.channel = match.channel
        self.confirm_func = None

        self.add_callbacks(self.ih)

    async def callback_check(self, interaction):
        if self.match.status is MatchStatus.IS_RUNNING:
            raise interactions.InteractionInvalid("Match is running!")
        i_ctx = InteractionContext(interaction)
        captain = await get_check_captain(i_ctx, self.match, check_turn=False)
        if not captain:
            raise interactions.InteractionNotAllowed
        return i_ctx, captain

    def add_callbacks(self, ih):
        @self.ih.callback('accept')
        async def accept(player, interaction_id, interaction, values):
            interaction_ctx, captain = await self.callback_check(interaction)
            ctx = ContextWrapper.wrap(self.match.channel, author=interaction.user)
            if captain is not self.expected:
                await disp.CONFIRM_NOT_CAPTAIN.send(interaction_ctx, self.expected.mention)
                raise interactions.InteractionNotAllowed
            elif self.confirm_func:
                kwargs = self.kwargs
                self.clean()
                await self.confirm_func(ctx, **kwargs)
            else:
                raise interactions.InteractionInvalid("no confirm function!")

        @self.ih.callback('decline')
        async def decline(player, interaction_id, interaction, values):
            interaction_ctx, captain = await self.callback_check(interaction)
            ctx = ContextWrapper.wrap(self.match.channel, author=interaction.user)
            self.clean()
            if captain is self.expected:
                await disp.CONFIRM_DECLINE.send(ctx)
            else:
                await disp.CONFIRM_CANCELED.send(ctx)

    def is_captain(self, captain):
        if not captain.is_captain:
            return False
        for tm in self.match.teams:
            if captain is tm.captain:
                return True
        return False

    def clean(self):
        self.ih.clean()
        self.expected = None
        self.kwargs = dict()

    def confirm(self, func):
        self.confirm_func = func
        return func

    async def force_confirm(self, ctx, **kwargs):
        if self.confirm_func:
            self.clean()
            await self.confirm_func(ctx, **kwargs)

    def arm(self, ctx, captain, **kwargs):
        if not self.is_captain(captain):
            raise UnexpectedError("Request from unknown player!")
        other = self.match.teams[captain.team.id - 1].captain
        self.expected = other
        self.kwargs = kwargs
        return self.ih.get_new_context(ctx)
