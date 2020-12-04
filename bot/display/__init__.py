"""Discord bot display module

It contains all the functions and the strings that can be outputted by 
the bot.

It must be used by the rest of the program for all the messages sent by
the bot.

All the strings sent can then be modified easily in this file.

Import this module and use only the following public function:

    * send(string_name, ctx, *args, **kwargs)
    * edit(string_name, ctx, *args, **kwargs)

"""

__all__ = ["init", "send", "edit", "image_send"]

from display import strings

import logging

log = logging.getLogger("pog_bot")

_client = None

def init(client):
    global _client
    _client = client


async def send(string_name, ctx, *args, **kwargs):
    """ Send the message string_name in context ctx,
        with additional strings *args.
        Pass **kwargs to the embed function, if any.
        Returns the message sent.
    """
    if not isinstance(ctx, SendCtx):
        ctx = SendCtx.wrap(ctx)
    kwargs = strings.AllStrings[string_name].value.get_elements(ctx,
        string = args, embed = kwargs)
    return await ctx.send(**kwargs)


async def edit(string_name, msg, *args, **kwargs):
    """ Replaces the message ctx by the message string_name, with additional strings *args. Pass **kwargs to the embed function, if any
        Returns the message sent
    """
    kwargs = strings.AllStrings[string_name].value.get_elements(msg,
        string = args, embed = kwargs)
    return await msg.edit(**kwargs)


async def image_send(string_name, ctx, image_path, *args):
    if not isinstance(ctx, SendCtx):
        ctx = SendCtx.wrap(ctx)
    kwargs = strings.AllStrings[string_name].value.get_elements(ctx,
        string = args, image = image_path)
    return await ctx.send(**kwargs)


class SendCtx:
    @classmethod
    def wrap(cls, ctx):
        try:
            cmd_name = ctx.command.name
        except AttributeError:
            cmd_name = "?"
        try:
            channel_id = ctx.channel.id
        except AttributeError:
            channel_id = 0
        try:
            author = ctx.author
        except AttributeError:
            author = None
        return cls(author, cmd_name, channel_id, ctx.send)

    @classmethod
    def user(cls, user_id):
        user = _client.get_user(user_id)
        return cls(user, "x", 0, user.send)

    @classmethod
    def channel(cls, channel_id, cmd_name = "x"):
        channel = _client.get_channel(channel_id)
        return cls(None, cmd_name, channel_id, channel.send)

    def __init__(self, author, cmd_name, channel_id, send):
        self.author = author
        self.cmd_name = cmd_name
        self.channel_id = channel_id
        self.send = send
