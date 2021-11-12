from modules.tools import UnexpectedError
from .interactions import CaptainInteractionHandler, InteractionNotAllowed, InteractionInvalid

from display import AllStrings as disp, ContextWrapper, InteractionContext, views


class CaptainValidator:
    def __init__(self, match):
        self.ih = CaptainInteractionHandler(match, views.validation_buttons, check_turn=False, disable_after_use=True)
        self.match = match
        self.expected = None
        self.kwargs = dict()
        self.channel = match.channel
        self.confirm_func = None

        self.add_callbacks(self.ih)

    def add_callbacks(self, ih):
        @self.ih.callback('accept')
        async def accept(captain, interaction_id, interaction, values):
            if captain is not self.expected:
                i_ctx = InteractionContext(interaction)
                await disp.CONFIRM_NOT_CAPTAIN.send(i_ctx, self.expected.mention)
                raise InteractionNotAllowed
            elif self.confirm_func:
                ctx = ContextWrapper.wrap(self.match.channel, author=interaction.user)
                kwargs = self.kwargs
                self.clean()
                await self.confirm_func(ctx, **kwargs)
            else:
                raise InteractionInvalid("no confirm function!")

        @self.ih.callback('decline')
        async def decline(captain, interaction_id, interaction, values):
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
