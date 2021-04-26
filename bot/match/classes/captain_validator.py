import modules.reactions as reactions
from modules.tools import UnexpectedError

from display import AllStrings as disp, ContextWrapper
from match import MatchStatus


class CaptainValidator:
    def __init__(self, match):
        self.rh = reactions.SingleMessageReactionHandler(rem_bot_react=True)
        self.match = match
        self.expected = None
        self.kwargs = dict()
        self.channel = match.channel
        self.confirm_func = None

        @self.rh.reaction('✅', "❌")
        async def reaction_confirm(reaction, player, user, msg):
            if self.match.status is MatchStatus.IS_RUNNING:
                raise reactions.UserLackingPermission
            if player.active:
                a_p = player.active
                ctx = ContextWrapper.wrap(self.channel)
                ctx.author = user
                if a_p is self.expected:
                    if str(reaction) == "❌":
                        self.clean()
                        await disp.CONFIRM_DECLINE.send(ctx)
                        return
                    elif self.confirm_func:
                        kwargs = self.kwargs
                        self.clean()
                        await self.confirm_func(ctx, **kwargs)
                        return
                elif self.is_captain(a_p) and str(reaction) == "❌":
                    self.clean()
                    await disp.CONFIRM_CANCELED.send(ctx)
                    return
            raise reactions.UserLackingPermission

    def is_captain(self, captain):
        for tm in self.match.teams:
            if captain is tm.captain:
                return True
        return False

    def clean(self):
        self.rh.clear()
        self.expected = None
        self.kwargs = dict()

    def confirm(self, func):
        self.confirm_func = func
        return func

    async def force_confirm(self, ctx, **kwargs):
        if self.confirm_func:
            self.clean()
            await self.confirm_func(ctx, **kwargs)

    async def wait_valid(self, captain, msg, **kwargs):
        if not self.is_captain(captain):
            raise UnexpectedError("Request from unknown player!")
        other = self.match.teams[captain.team.id - 1].captain
        self.expected = other
        self.kwargs = kwargs
        await self.rh.set_new_msg(msg)

    async def check_message(self, ctx, captain, args):
        if len(args) == 1:
            if args[0] == "accept" or args[0] == "a":
                if not self.expected:
                    await disp.CONFIRM_NOTHING.send(ctx)
                elif captain is not self.expected:
                    await disp.CONFIRM_NOT_CAPTAIN.send(ctx, self.expected.mention)
                elif self.confirm_func:
                    kwargs = self.kwargs
                    self.clean()
                    await self.confirm_func(ctx, **kwargs)
                else:
                    raise UnexpectedError("Confirm Function is None!")
                return True
            elif args[0] == "decline" or args[0] == "d":
                if not self.expected:
                    await disp.DECLINE_NOTHING.send(ctx)
                elif captain is not self.expected:
                    if self.is_captain(captain):
                        self.clean()
                        await disp.CONFIRM_CANCELED.send(ctx)
                    else:
                        await disp.DECLINE_NOT_CAPTAIN.send(ctx, self.expected.mention)
                else:
                    self.clean()
                    await disp.CONFIRM_DECLINE.send(ctx)
                return True
            elif args[0] == "cancel" or args[0] == "c":
                if not self.expected:
                    await disp.CANCEL_NOTHING.send(ctx)
                elif self.is_captain(captain) and (captain is not self.expected):
                    self.clean()
                    await disp.CONFIRM_CANCELED.send(ctx)
                else:
                    await disp.CANCEL_NOT_CAPTAIN.send(ctx)
                return True
        return False
