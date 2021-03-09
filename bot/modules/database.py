# @CHECK 2.0 features OK

"""Handle mongodb interaction
"""

# External modules
from pymongo import MongoClient
from asyncio import get_event_loop

# Custom modules:
from general.exceptions import DatabaseError

# dict for the collections
collections = dict()


# Public
def get_all_items(init_class_method, db_name):
    items = collections[db_name].find()
    # Adding them
    try:
        for result in items:
            init_class_method(result)
    except KeyError as e:
        raise DatabaseError(f"KeyError when retrieving {db_name} from database: {e}")

async def get_one_item(db_name, item_id):
    loop = get_event_loop()
    await loop.run_in_executor(None, _get_one_item, db_name, item_id)

async def update_player(p, doc):
    """ Launch the task updating player p in database
    """
    loop = get_event_loop()
    await loop.run_in_executor(None, _update_player, p, doc)

async def update_match(m):
    loop = get_event_loop()
    await loop.run_in_executor(None, _add_match, m)

async def remove_player(p):
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


def force_update(db_name, elements):
    """ This is only called from external script for db maintenance
    """
    collections[db_name].delete_many({})
    collections[db_name].insert_many(elements)


# Private
def _update_player(p, doc):
    """ Update player p into db
    """
    if collections["users"].count_documents({"_id": p.id}) != 0:
        collections["users"].update_one({"_id": p.id}, {"$set": doc})
    else:
        collections["users"].insert_one(p.get_data())

def _get_one_item(db_name, item_id):
    if collections[db_name].count_documents({"_id": item_id}) == 0:
        raise DatabaseError(f"Item [id:{item_id}] not found in collection 'db_name'")
    item = collections[db_name].find_one({"_id": item_id})
    try:
        return item
    except KeyError as e:
        raise DatabaseError(f"KeyError when retrieving {db_name} from database: {e}")

def _replace_player(p):
    """ Update player p into db
    """
    if collections["users"].count_documents({"_id": p.id}) != 0:
        collections["users"].replace_one({"_id": p.id}, p.get_data())
    else:
        collections["users"].insert_one(p.get_data())

def _update_base(m):
    """ Update base m into db
    """
    if collections["s_bases"].count_documents({"_id": m.id}) != 0:
        collections["s_bases"].update_one({"_id": m.id}, {"$set": m.get_data()})
    else:
        raise DatabaseError(f"Map {m.id} not in database")


def _remove(p):
    if collections["users"].count_documents({"_id": p.id}) != 0:
        collections["users"].delete_one({"_id": p.id})
    else:
        raise DatabaseError(f"Player {p.id} not in database")

def _add_match(m):
    """ Update player p into db
    """
    if collections["matches"].count_documents({"_id": m.number}) != 0:
        raise DatabaseError(f"Match {m.number} already in database!")
    else:
        collections["matches"].insert_one(m.get_data())
