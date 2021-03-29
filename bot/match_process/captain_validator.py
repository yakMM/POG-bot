import modules.reactions as reactions
from modules.tools import UnexpectedError

from display import AllStrings as disp, ContextWrapper


class CaptainValidator:
    def __init__(self, cap_1, cap_2, channel):
        self.rh = reactions.SingleMessageReactionHandler(rem_bot_react=True)
        self.captains = [cap_1, cap_2]
        self.expected = None
        self.channel = channel
        self.is_invalid_func = None
        self.confirm_func = None

    async def clean(self):
        await self.rh.destroy()
        self.expected = None

    def is_invalid(self, *args):
        def decorator(func):
            self.is_invalid_func = func
            return func
        return decorator

    def confirm(self, *args):
        def decorator(func):
            self.confirm_func = func
            return func
        return decorator

    async def force_confirm(self, ctx, captain):
        if self.confirm_func:
            await self.confirm_func(ctx, captain)
            await self.clean()

    async def wait_valid(self, captain, msg):
        if captain not in self.captains:
            raise UnexpectedError("Request from unknown player!")
        for cap in self.captains:
            if captain is not cap:
                self.expected = cap

        @self.rh.reaction('✅')
        async def reaction_confirm(reaction, player, user):
            if player.active and player.active is self.expected:
                ctx = ContextWrapper.wrap(self.channel)
                ctx.author = user
                if self.confirm_func:
                    await self.confirm_func(ctx, player.active)
                    await self.clean()
            else:
                raise reactions.UserLackingPermission

        await self.rh.set_new_msg(msg)

    async def check_message(self, ctx, captain, args):
        if len(args) == 1 and args[0] == "confirm":
            if self.is_invalid_func and await self.is_invalid_func(ctx, captain):
                pass
            elif not self.expected:
                await disp.CONFIRM_NOTHING.send(ctx)
            elif captain is not self.expected:
                await disp.CONFIRM_NOT_CAPTAIN.send(ctx, self.expected.mention)
            elif self.confirm_func:
                await self.confirm_func(ctx, captain)
                await self.clean()
            else:
                raise UnexpectedError("Confirm Function is None!")
            return True
        return False
