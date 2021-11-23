from modules.spam_checker import is_spam, unlock
from discord import Interaction
from logging import getLogger
from inspect import iscoroutinefunction as is_coroutine
from discord.errors import NotFound
from lib.tasks import Loop
from display import ContextWrapper, InteractionContext
from modules.roles import is_admin

log = getLogger("pog_bot")


class InteractionNotAllowed(Exception):
    pass


class InteractionInvalid(Exception):
    def __init__(self, msg):
        self.reason = msg
        message = "Invalid interaction: " + msg
        log.error(message)
        super().__init__(message)


class InteractionPayload:
    def __init__(self, ih, owner, view):
        self.callback = ih.run
        self.message_callback = ih.message_callback
        self.view = view
        self.owner = owner


class InteractionHandler:
    def __init__(self, owner, view, disable_after_use=True, single_callback=None, is_admin_allowed=False):
        self.__disable_after_use = disable_after_use
        self.__is_admin_allowed = is_admin_allowed
        self.__f_dict = dict()
        self.__callback = single_callback
        self.__msg = None
        self.__view = None
        self.__locked = False
        self.__payload = InteractionPayload(self, owner, view)

    def get_new_context(self, ctx):
        self.__locked = True
        if self.__msg:
            self.clean()
        ctx = ContextWrapper.wrap(ctx)
        ctx.interaction_payload = self.__payload
        return ctx

    def message_callback(self, msg, kwargs):
        self.clean()
        self.__msg = msg
        self.__view = kwargs['view']
        self.__locked = False

    async def run_player_check(self, interaction):
        # For inheritance purposes
        return None

    def __is_admin(self, user):
        return self.__is_admin_allowed and is_admin(user)

    async def run(self, interaction: Interaction):
        if self.__locked:
            return

        user = interaction.user
        player = None

        if await is_spam(user, interaction.message.channel, ctx=InteractionContext(interaction)):
            return

        self.__locked = True

        interaction_id = interaction.data['custom_id']
        interaction_values = interaction.data.get('values', None)

        try:
            if not self.__is_admin(user):
                player = await self.run_player_check(interaction)
            if not self.__callback:
                funcs = self.__f_dict[interaction_id]
            else:
                funcs = [self.__callback]
            for func in funcs:
                if is_coroutine(func):
                    await func(player, interaction_id, interaction, interaction_values)
                else:
                    func(interaction_id, interaction, interaction_values)
                if self.__disable_after_use:
                    self.clean()
        except (InteractionNotAllowed, InteractionInvalid):
            pass
        except KeyError as e:
            log.warning(f"KeyError when processing interaction: {e}")
        except NotFound as e:
            log.warning(f"NotFound when processing interaction: {e}")
        finally:
            self.__locked = False
            unlock(user.id)

    def add_callback(self, custom_id, fct):
        if custom_id not in self.__f_dict:
            self.__f_dict[custom_id] = list()
        self.__f_dict[custom_id].append(fct)

    def callback(self, *args):
        def decorator(func):
            for custom_id in args:
                self.add_callback(custom_id, func)
            return func
        return decorator

    def clean(self):
        self.__locked = True
        if self.__msg:
            for child in self.__view.children:
                child.disabled = True
                # Fix for https://github.com/discord/discord-api-docs/issues/4148
                # TODO: Just empty the view when the issue is fixed
            self.__view.stop()
            Loop(coro=self._remove_msg, count=1).start(self.__msg, self.__view)
        self.__msg = None
        self.__view = None

    async def _remove_msg(self, msg, view):
        try:
            ctx = ContextWrapper.wrap(msg)
            await ctx.edit(view=view)
        except NotFound:
            log.warning("NotFound exception when trying to remove message!")
