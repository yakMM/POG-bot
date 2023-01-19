# @CHECK 2.0 features OK

from discord.ext.commands.errors import ExtensionAlreadyLoaded

main_cogs = ["cogs.admin"]
standard_cogs = ["cogs.register", "cogs.matches", "cogs.lobby", "cogs.muted", "cogs.common", "cogs.usage"]
__is_global_locked = True  # Lock the bot from getting messages


async def init(client):
    for cog in main_cogs:
        await client.load_extension(cog)


async def lock_all(client):
    for cog in standard_cogs:
        await client.unload_extension(cog)
    global __is_global_locked
    __is_global_locked = True


async def unlock_all(client):
    for cog in standard_cogs:
        try:
            await client.load_extension(cog)
        except ExtensionAlreadyLoaded:
            pass
    global __is_global_locked
    __is_global_locked = False


def is_all_locked():
    global __is_global_locked
    return __is_global_locked
