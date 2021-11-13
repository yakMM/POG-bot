from modules.spam_checker import is_spam, unlock
from discord import Interaction
from logging import getLogger
from inspect import iscoroutinefunction as is_coroutine
from discord.errors import NotFound
from lib.tasks import Loop
from display import ContextWrapper
from classes import Player
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
        self.__locked = False
        self.__payload = InteractionPayload(self, owner, view)

    def get_new_context(self, ctx):
        self.__locked = True
        if self.__msg:
            self.clean()
        ctx = ContextWrapper.wrap(ctx)
        ctx.interaction_payload = self.__payload
        return ctx

    def message_callback(self, msg):
        if self.__msg:
            self.clean()
        self.__msg = msg
        self.__locked = False

    async def run_player_check(self, player, interaction):
        # For inheritance purposes
        return player

    def __is_admin(self, user):
        return is_admin(user) and self.__is_admin_allowed

    async def run(self, interaction: Interaction):
        if self.__locked:
            return

        user = interaction.user

        player = Player.get(interaction.user.id)
        if not player and not self.__is_admin(user):
            return

        if await is_spam(user, interaction.message.channel):
            return

        self.__locked = True

        interaction_id = interaction.data['custom_id']
        interaction_values = interaction.data.get('values', None)

        try:
            player = await self.run_player_check(player, interaction)
            if not player and not self.__is_admin(user):
                raise InteractionNotAllowed
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
            Loop(coro=self._remove_msg, count=1).start(self.__msg)
        self.__msg = None

    async def _remove_msg(self, msg):
        try:
            await msg.edit(view=None)
        except NotFound:
            pass
