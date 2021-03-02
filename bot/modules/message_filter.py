# @CHECK 2.0 features OK

"""Tiny module used as a slight spam protector
"""

from display.strings import AllStrings as display
from display.classes import ContextWrapper
from discord import DMChannel
import modules.config as cfg
from modules.loader import is_all_locked
from modules.roles import is_admin
from asyncio import sleep

__spam_list = dict()
__SPAM_MSG_FREQUENCY = 5


async def is_spam(msg):
    id = msg.author.id
    if id not in __spam_list:
        __spam_list[id] = 1
        return False
    __spam_list[id] += 1
    if __spam_list[id] == 1:
        return False
    if __spam_list[id] % __SPAM_MSG_FREQUENCY == 0:
        await display.STOP_SPAM.send(msg)
    return True


# This is never called:
def clean():
    tmp = __spam_list.copy()
    for id in tmp:
        if __spam_list[id] == 0:
            del __spam_list[id]


def unlock(id):
    __spam_list[id] = 0


async def on_message(client, message):

    # if bot, do nothing
    if message.author == client.user:
        return

    # if dm, send in staff
    if isinstance(message.channel, DMChannel):
        await display.BOT_DM.send(ContextWrapper.channel(cfg.channels["staff"]), msg=message)
        await display.BOT_DM_RECEIVED.send(message.author)
        return

    
    if message.channel.id not in cfg.channels_list:
        return
    if is_all_locked():
        if not is_admin(message.author):
            return
        # Admins can still use bot when locked
    actual_author = message.author
    if await is_spam(message):
        return
    message.content = message.content.lower()
    if is_admin(message.author) and message.content[0:3] == "=as":
        if message.mentions:
            message.author = message.mentions[0]
            del message.mentions[0]
            try:
                i = message.content[1:].index('=')
                message.content = message.content[i+1:]
                await client.process_commands(message)
            except ValueError:
                await display.WRONG_USAGE.send(message.channel, "as")
    else:
        await client.process_commands(message)  # if not spam, process
    await sleep(0.5)
    unlock(actual_author.id)  # call finished, we can release user