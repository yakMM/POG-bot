"""Tiny module used as a slight spam protector
"""

from display import AllStrings as disp, ContextWrapper
from discord import DMChannel, NotFound
import modules.config as cfg
from modules.loader import is_all_locked
from modules.roles import is_admin
from asyncio import sleep
import modules.spam_checker as spam_checker
from modules.dm_handler import on_dm


class FakeMember:
    def __init__(self, id):
        self.id = id
        self.name = "Unknown"

    @property
    def mention(self):
        return f'<@{self.id}>'



async def on_message(client, message):

    # if bot, do nothing
    if message.author == client.user:
        return

    # if dm, send in staff
    if isinstance(message.channel, DMChannel):
        await on_dm(message)
        return

    # If message not in the bot's area of action
    if message.channel.id not in cfg.channels_list:
        return

    if len(message.content) == 0:
        return

    if message.content == cfg.emojis['info']:
        message.content = "=info"

    if message.content[0] != cfg.general["command_prefix"]:
        return

    # If bot is locked
    if is_all_locked():
        if not is_admin(message.author):
            return
        # Admins can still use bot when locked

    # Save actual author
    actual_author = message.author

    # Check if too many requests from this user:
    if await spam_checker.is_spam(message.author, message.channel):
        return

    try:
        # Make the message lower-case:
        if not message.content.lower().startswith("=rename"):
            message.content = message.content.lower()

        message.content = message.content.replace(",", " ").replace("/", " ").replace(";", " ")

        # Split on whitespaces
        args = message.content.split()

        new_args = list()
        for arg in args:
            if '@' in arg:
                continue
            try:
                arg_int = int(arg)
            except ValueError:
                pass
            else:
                if arg_int >= 21154535154122752:  # minimum number for discord id
                    member = message.channel.guild.get_member(arg_int)
                    if member:
                        message.mentions.append(member)
                        continue
                    try:
                        member = await message.channel.guild.fetch_member(arg_int)
                    except NotFound:
                        message.mentions.append(FakeMember(arg_int))
                        continue
                    if member:
                        message.mentions.append(member)
                        continue

            new_args.append(arg)

        message.content = " ".join(new_args)

        # Check for =as command
        if is_admin(message.author) and message.content[0:3] == "=as":
            try:
                message.author = message.mentions[0]
                del message.mentions[0]
                i = message.content[1:].index('=')
                message.content = message.content[i+1:]
            except (ValueError, IndexError):
                ctx = ContextWrapper.wrap(message.channel, author=actual_author)
                await disp.WRONG_USAGE.send(ctx, "as")
                spam_checker.unlock(actual_author.id)
                return

        await client.process_commands(message)  # if not spam, processes

        # Call finished, we can release user
        await sleep(0.5)
    finally:
        spam_checker.unlock(actual_author.id)
