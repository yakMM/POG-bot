from discord import File, ui
import modules.config as cfg
from logging import getLogger
from aiohttp.client_exceptions import ClientError
from discord.backoff import ExponentialBackoff
import asyncio
from modules.tools import UnexpectedError

log = getLogger("pog_bot")


class Message:
    """ Class for the enum to use
    """
    def __init__(self, string, ping=True, embed=None):
        self.__str = string
        self.__embed_fct = embed
        self.__ping = ping

    def get_ui(self, ctx, elements, kwargs):
        if self.__embed_fct:
            embed = self.__embed_fct(ctx, **kwargs)
            # Fixes the embed mobile bug:
            embed.set_author(name="Planetside Open Games",
            url="https://docs.google.com/document/d/13rsrWA4r16gpB-F3gvx5HWf2T974mdHLraPSjh5DO1Q/",
            icon_url = "https://media.discordapp.net/attachments/739231714554937455/739522071423614996/logo_png.png")

            elements['embed'] = embed
        if ctx.interaction_payload:
            try:
                view = ctx.interaction_payload.view(ctx)
                elements['view'] = view
            except TypeError as e:
                log.warning(f"TypeError when getting view: {e}")

    def get_string(self, ctx, elements, args):
        if self.__str:
            # Format the string to be sent with added args
            string = self.__str.format(*args)

            if self.__ping:
                try:
                    mention = ctx.author.mention
                    string = f'{mention} {string}'
                except AttributeError:
                    pass

            elements['content'] = string

    def get_image(self, ctx, elements, image_path):
        if image_path:
            elements['file'] = File(image_path)

    def get_elements(self, ctx, **kwargs):

        elements = dict()
        self.get_string(ctx, elements, kwargs.get('string_args'))
        self.get_ui(ctx, elements, kwargs.get('ui_kwargs'))
        self.get_image(ctx, elements, kwargs.get('image_path'))

        return elements


class ContextWrapper:

    client = None

    @classmethod
    def init(cls, client):
        cls.client = client

    @classmethod
    def wrap(cls, ctx, author=None):
        if isinstance(ctx, cls):
            cmd_name = ctx.cmd_name
            channel_id = ctx.channel_id
            author = ctx.author
            message = ctx.message
            original_ctx = ctx.original_ctx
            return cls(author, cmd_name, channel_id, message, original_ctx)
        try:
            cmd_name = ctx.command.name
        except AttributeError:
            cmd_name = "?"
        try:
            channel_id = ctx.channel.id
        except AttributeError:
            channel_id = 0
        if not author:
            try:
                author = ctx.author
            except AttributeError:
                pass
        if not author:
            try:
                author = ctx.user
            except AttributeError:
                pass
        try:
            message = ctx.message
        except AttributeError:
            message = None
        return cls(author, cmd_name, channel_id, message, ctx)

    @classmethod
    def user(cls, user_id):
        user = cls.client.get_user(user_id)
        return cls(user, "?", user_id, None, user)

    @classmethod
    def channel(cls, channel_id, cmd_name="?"):
        channel = cls.client.get_channel(channel_id)
        return cls(None, cmd_name, channel_id, None, channel)

    def __init__(self, author, cmd_name, channel_id, message, original_ctx):
        self.author = author
        self.cmd_name = cmd_name
        self.channel_id = channel_id
        self.original_ctx = original_ctx
        self.message = message
        self.interaction_payload = None

    async def send(self, **kwargs):
        return await self._do_send('send', kwargs)

    async def edit(self, **kwargs):
        return await self._do_send('edit', kwargs)

    async def _do_send(self, command, kwargs):
        backoff = ExponentialBackoff()
        for i in range(5):
            try:
                if i != 0:
                    await asyncio.sleep(backoff.delay())
                msg = await getattr(self.original_ctx, command)(**kwargs)
                if self.interaction_payload:
                    self.interaction_payload.message_callback(msg, kwargs)
                return msg
            except ClientError as e:
                log.warning(f"ContextWrapper: Network error when sending message on try {i}!"
                            f"\n {e}")
        log.error(f"ContextWrapper: Network error when sending message after 5 retries! Giving up...")
        raise UnexpectedError("ContextWrapper could not send message after 5 retries!")


class InteractionContext(ContextWrapper):
    def __init__(self, interaction, ephemeral=True):
        cmd_name = "?"
        channel_id = interaction.channel_id
        author = interaction.user
        message = interaction.message
        ctx = interaction.response
        self.ephemeral = ephemeral
        super().__init__(author, cmd_name, channel_id, message, ctx)

    async def send(self, **kwargs):
        if self.ephemeral:
            kwargs['ephemeral'] = True
        return await self._do_send('send_message', kwargs)



