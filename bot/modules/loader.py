main_cogs = ["cogs.admin"]
standard_cogs = ["cogs.register", "cogs.matches", "cogs.lobby"]
__isGlobalLocked = True # Lock the bot from getting messages

def init(client):
    for cog in main_cogs:
        client.load_extension(cog)

def lockAll(client):
    for cog in standard_cogs:
        client.unload_extension(cog)
    global __isGlobalLocked
    __isGlobalLocked = True

def unlockAll(client):
    for cog in standard_cogs:
        client.load_extension(cog)
    global __isGlobalLocked
    __isGlobalLocked = False

def isAllLocked():
    global __isGlobalLocked
    return __isGlobalLocked