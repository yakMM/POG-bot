"""Tiny module used as a slight spam protector
"""

from display import AllStrings as disp, ContextWrapper
from discord import DMChannel
import modules.config as cfg
from modules.loader import is_all_locked
from modules.roles import is_admin
from asyncio import sleep
import modules.tools as tools
from logging import getLogger

__spam_list = dict()
__SPAM_MSG_FREQUENCY = 5
__last_requests = dict()

log = getLogger("pog_bot")


async def is_spam(author, channel):
    a_id = author.id
    if a_id in __spam_list and __spam_list[a_id] > 0:
        if a_id in __last_requests and __last_requests[a_id] < tools.timestamp_now() - 30:
            log.info(f"Automatically unlocked id[{a_id}], name[{author.name}] from spam filter")
            unlock(a_id)
    __last_requests[a_id] = tools.timestamp_now()
    if a_id not in __spam_list:
        __spam_list[a_id] = 1
        return False
    __spam_list[a_id] += 1
    if __spam_list[a_id] == 1:
        return False
    if __spam_list[a_id] % __SPAM_MSG_FREQUENCY == 0:
        ctx = ContextWrapper.wrap(channel)
        ctx.author = author
        await disp.STOP_SPAM.send(ctx)
    return True


# This is never called:
def clean():
    tmp = __spam_list.copy()
    for a_id in tmp:
        if __spam_list[a_id] == 0:
            del __spam_list[a_id]


def debug():
    result = dict()
    for k in list(__spam_list.keys()):
        if __spam_list[k] > 0:
            result[k] = __spam_list[k]
    return result


def clear_spam_list():
    __spam_list.clear()


def unlock(a_id):
    __spam_list[a_id] = 0


async def on_message(client, message):

    # if bot, do nothing
    if message.author == client.user:
        return

    # if dm, send in staff
    if isinstance(message.channel, DMChannel):
        await disp.BOT_DM.send(ContextWrapper.channel(cfg.channels["staff"]), msg=message)
        await disp.BOT_DM_RECEIVED.send(message.author)
        return

    # If message not in the bot's area of action
    if message.channel.id not in cfg.channels_list:
        return

    # If bot is locked
    if is_all_locked():
        if not is_admin(message.author):
            return
        # Admins can still use bot when locked

    # Save actual author
    actual_author = message.author

    # Check if too many requests from this user:
    if await is_spam(message.author, message.channel):
        return

    # Make the message lower-case:
    if not message.content.lower().startswith("=rename"):
        message.content = message.content.lower()

    # Automatically add a mention if a discord id is in the message:
    args = message.content.split(" ")
    for arg in args:
        try:
            arg_int = int(arg)
            if arg_int >= 21154535154122752:  # minimum number for discord id
                member = message.channel.guild.get_member(arg_int)
                if member:
                    message.mentions.append(member)
        except ValueError:
            pass

    # Meme
    if client.user in message.mentions and "u dumb" in message.content:
        await disp.BOT_U_DUMB.send(message.channel)

    # Check for =as command
    if is_admin(message.author) and message.content[0:3] == "=as":
        if message.mentions:
            message.author = message.mentions[0]
            del message.mentions[0]
            try:
                i = message.content[1:].index('=')
                message.content = message.content[i+1:]
                await client.process_commands(message)
            except ValueError:
                await disp.WRONG_USAGE.send(message.channel, "as")
    else:
        await client.process_commands(message)  # if not spam, processes

    # Call finished, we can release user
    await sleep(0.5)
    unlock(actual_author.id)
