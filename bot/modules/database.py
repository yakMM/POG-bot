"""Handle mongodb interaction
"""

# External modules
from pymongo import MongoClient
from asyncio import get_event_loop

# Custom modules:
from modules.exceptions import DatabaseError

# dict for the collections
collections = dict()

# Public

def getAllItems(initClassMethod, dbName):
    items = collections[dbName].find()
    # Adding them
    try:
        for result in items:
            initClassMethod(result)
    except KeyError as e:
        raise DatabaseError(f"KeyError when retrieving {dbName} from database: {e}")


async def updatePlayer(p, doc):
    """ Launch the task updating player p in database
    """
    loop = get_event_loop()
    await loop.run_in_executor(None, _updatePlayer, p, doc)


async def removePlayer(p):
    """ Launch the task updating player p in database
    """
    loop = get_event_loop()
    await loop.run_in_executor(None, _remove, p)


def init(config):
    """ Init"""
    cluster = MongoClient(config["url"])
    db = cluster[config["cluster"]]
    for collec in config["collections"]:
        collections[collec] = db[config["collections"][collec]]


def forceUpdate(db_name, elements):
    """ This is only called from external script for db maintenance
    """
    collections[db_name].delete_many({})
    collections[db_name].insert_many(elements)


# Private
def _updatePlayer(p, doc):
    """ Update player p into db
    """
    if collections["users"].count_documents({"_id": p.id}) != 0:
        collections["users"].update_one({"_id": p.id}, {"$set": doc})
    else:
        collections["users"].insert_one(p.getData())


def _replacePlayer(p):
    """ Update player p into db
    """
    if collections["users"].count_documents({"_id": p.id}) != 0:
        collections["users"].replace_one({"_id": p.id}, p.getData())
    else:
        collections["users"].insert_one(p.getData())


def _updateMap(m):
    """ Update map m into db
    """
    if collections["sBases"].count_documents({"_id": m.id}) != 0:
        collections["sBases"].update_one({"_id": m.id}, {"$set": m.getData()})
    else:
        raise DatabaseError(f"Map {m.id} not in database")


def _remove(p):
    if collections["users"].count_documents({"_id": p.id}) != 0:
        collections["users"].delete_one({"_id": p.id})
    else:
        raise DatabaseError(f"Player {p.id} not in database")
