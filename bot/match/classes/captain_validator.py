import modules.reactions as reactions
import modules.interactions as interactions
from modules.tools import UnexpectedError

from display import AllStrings as disp, ContextWrapper
from match import MatchStatus
from classes import Player
import modules.config as cfg


class CaptainValidator:
    def __init__(self, match):
        self.ih = interactions.InteractionHandler(disable_after_use=True)
        self.match = match
        self.expected = None
        self.kwargs = dict()
        self.channel = match.channel
        self.confirm_func = None

        @self.ih.callback('accept', 'decline')
        async def interaction_result(interaction_id, interaction, values):
            if self.match.status is MatchStatus.IS_RUNNING:
                raise interactions.InteractionInvalid("Match is running!")
            user = interaction.user
            player = Player.get(user.id)
            if not player:
                raise interactions.InteractionNotAllowed
            interaction_ctx = ContextWrapper.wrap(interaction.response, ephemeral=True)
            if player.active:
                a_p = player.active
                ctx = ContextWrapper.wrap(self.channel)
                ctx.author = user
                if not self.is_captain(a_p):
                    await disp.PK_NOT_CAPTAIN.send(
                        interaction_ctx)
                    raise interactions.InteractionNotAllowed
                if interaction_id == "accept":
                    if a_p is not self.expected:
                        await disp.CONFIRM_NOT_CAPTAIN.send(
                            interaction_ctx,
                            self.expected.mention)
                        raise interactions.InteractionNotAllowed
                    elif self.confirm_func:
                        kwargs = self.kwargs
                        self.clean()
                        await self.confirm_func(ctx, **kwargs)
                    else:
                        raise interactions.InteractionInvalid("no confirm function!")
                elif interaction_id == "decline":
                    if a_p is self.expected:
                        self.clean()
                        await disp.CONFIRM_DECLINE.send(ctx)
                    else:
                        self.clean()
                        await disp.CONFIRM_CANCELED.send(ctx)
            elif player.match:
                await disp.PK_WAIT_FOR_PICK.send(interaction_ctx)
                raise interactions.InteractionNotAllowed
            else:
                await disp.PK_NO_LOBBIED.send(interaction_ctx,
                                                        cfg.channels["lobby"])
                raise interactions.InteractionNotAllowed

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
