"""Discord bot display module

It contains all the functions and the strings that can be outputted by 
the bot.

It must be used by the rest of the program for all the messages sent by
the bot.

All the strings sent can then be modified easily in this file.

Import this module and use only the following public function:

    * channel_send(string_name, id, *args, **kwargs)
    * private_send(string_name, id, *args, **kwargs)
    * send(string_name, ctx, *args, **kwargs)
    * edit(string_name, ctx, *args, **kwargs)

"""

__all__ = ["init", "channel_send", "private_send", "send", "edit", "image_send"]

from display import strings

import logging

log = logging.getLogger(__name__)

_client = None

def init(client):
    global _client
    _client = client


async def channel_send(string_name, c_id, *args, **kwargs):
    """ Send the message string_name in the channel identified with id,
        with additional strings *args.
        Pass **kwargs to the embed function, if any.
        Returns the message sent.
    """
    channel = _client.get_channel(c_id)
    kwargs = strings.AllStrings[string_name].value.get_elements(channel,
        string = args, embed = kwargs)
    return await channel.send(**kwargs)


async def private_send(string_name, u_id, *args, **kwargs):
    """ Send the message string_name in dm to user identified with id,
        with additional strings *args.
        Pass **kwargs to the embed function, if any.
        Returns the message sent.
    """
    user = _client.get_user(u_id)
    kwargs = strings.AllStrings[string_name].value.get_elements(user,
        strings = args, embed = kwargs)
    return await user.send(**kwargs)


async def send(string_name, ctx, *args, **kwargs):
    """ Send the message string_name in context ctx,
        with additional strings *args.
        Pass **kwargs to the embed function, if any.
        Returns the message sent.
    """
    kwargs = strings.AllStrings[string_name].value.get_elements(ctx,
        string = args, embed = kwargs)
    return await ctx.send(**kwargs)


async def edit(string_name, ctx, *args, **kwargs):
    """ Replaces the message ctx by the message string_name, with additional strings *args. Pass **kwargs to the embed function, if any
        Returns the message sent
    """
    kwargs = strings.AllStrings[string_name].value.get_elements(ctx,
        string = args, embed = kwargs)
    return await ctx.edit(**kwargs)


async def image_send(string_name, c_id, image_path, *args):
    channel = _client.get_channel(c_id)
    kwargs = strings.AllStrings[string_name].value.get_elements(channel,
        string = args, image = image_path)
    return await channel.send(**kwargs)