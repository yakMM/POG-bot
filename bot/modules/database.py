"""Handle mongodb interaction
"""

# External modules
from pymongo import MongoClient
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor

# Custom modules:
from modules.exceptions import DatabaseError

# Modules for the custom classes
# Circular import disclaimer: database.py is only imported by main.py, so it's fine to import the following:
from classes.players import Player # ok
from classes.maps import Map # ok

# dict for the collections
collections = dict()

## Public
def getAllPlayers():
    """ Get all players from db to memory
    """
    users = collections["users"].find()
    # Adding them
    try:
        for result in users:
            Player.newFromData(result)
    except KeyError:
        raise DatabaseError("KeyError when retrieving players")

def getAllMaps():
    """ Get all maps from db to memory
    """
    maps = collections["sBases"].find()
    # Adding them
    try:
        for result in maps:
            Map(result)
    except KeyError:
        raise DatabaseError("KeyError when retrieving maps")


async def update(p):
    """ Launch the task updating player p in database
    """
    loop = get_event_loop()
    await loop.run_in_executor(ThreadPoolExecutor(), _update, p)

async def remove(p):
    """ Launch the task updating player p in database
    """
    loop = get_event_loop()
    await loop.run_in_executor(ThreadPoolExecutor(), _remove, p)

def init(config):
    """ Init
    """
    cluster = MongoClient(config["url"])
    db = cluster[config["cluster"]]
    for collec in config["collections"]:
        collections[collec] = db[config["collections"][collec]]

def forceBasesUpdate(bases):
    """ This is only called from external script for db maintenance
    """
    collections["sBases"].delete_many({})
    collections["sBases"].insert_many(bases)


## Private
def _update(p):
    """ Update player p into db
    """
    if collections["users"].count_documents({ "_id": p.id }) != 0:
        collections["users"].update_one({"_id":p.id},{"$set":p.getData()})
    else:
        collections["users"].insert_one(p.getData())

def _remove(p):
    if collections["users"].count_documents({ "_id": p.id }) != 0:
        collections["users"].delete_one({"_id":p.id}) 
    else:
        raise DatabaseError(f"Player {p.id} not in database")