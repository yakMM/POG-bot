"""Discord bot display module

It contains all the functions and the strings that can be outputted by 
the bot.

It must be used by the rest of the program for all the messages sent by
the bot.

All the strings sent can then be modified easily in this file.

Import this module and use only the following public function:

    * channelSend(stringName, id, *args, **kwargs)
    * privateSend(stringName, id, *args, **kwargs)
    * send(stringName, ctx, *args, **kwargs)
    * edit(stringName, ctx, *args, **kwargs)

"""

__all__ = ["init", "channelSend", "privateSend", "send", "edit", "imageSend"]

from display import strings

import logging

log = logging.getLogger(__name__)

_client = None

def init(client):
    global _client
    _client = client

async def channelSend(stringName, cId, *args, **kwargs):
    """ Send the message stringName in the channel identified with id,
        with additional strings *args.
        Pass **kwargs to the embed function, if any.
        Returns the message sent.
    """
    channel = _client.get_channel(cId)
    kwargs = strings.AllStrings[stringName].value.getElements(channel,
        {"string" : args, "embed" : kwargs})
    return await channel.send(**kwargs)

async def privateSend(stringName, uId, *args, **kwargs):
    """ Send the message stringName in dm to user identified with id,
        with additional strings *args.
        Pass **kwargs to the embed function, if any.
        Returns the message sent.
    """
    user = _client.get_user(uId)
    kwargs = strings.AllStrings[stringName].value.getElements(user,
        {"string" : args, "embed" : kwargs})
    return await user.send(**kwargs)


async def send(string_name, ctx, *args, **kwargs):
    """ Send the message stringName in context ctx,
        with additional strings *args.
        Pass **kwargs to the embed function, if any.
        Returns the message sent.
    """
    return await strings.AllStrings[string_name].value.get_elements(ctx,
        {"string" : args, "embed" : kwargs})
    return await ctx.send(**kwargs)




async def edit(stringName, ctx, *args, **kwargs):
    """ Replaces the message ctx by the message stringName, with additional strings *args. Pass **kwargs to the embed function, if any
        Returns the message sent
    """
    return await StringEnum[stringName].value.display(ctx, ctx.edit,  *args, **kwargs)

async def imageSend(stringName, channelId, imagePath, *args):
    channel = _client.get_channel(channelId)
    return await channel.send(content=StringEnum[stringName].value.string.format(*args), file=File(imagePath))