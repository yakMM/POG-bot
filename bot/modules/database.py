# @CHECK 2.0 features OK

"""Handle mongodb interaction
"""

# External modules
from pymongo import MongoClient
from asyncio import get_event_loop
from logging import getLogger

log = getLogger("pog_bot")

# dict for the collections
collections = dict()


class DatabaseError(Exception):
    def __init__(self, msg):
        message = "Error in database: " + msg
        super().__init__(message)


def init(config):
    """ Init"""
    cluster = MongoClient(config["url"])
    db = cluster[config["cluster"]]
    for collection in config["collections"]:
        collections[collection] = db[config["collections"][collection]]


def get_all_elements(init_class_method, db_name):
    items = collections[db_name].find()
    # Adding them
    try:
        for result in items:
            init_class_method(result)
    except KeyError as e:
        raise DatabaseError(f"KeyError when retrieving {db_name} from database: {e}")


async def async_db_call(call, *args):
    loop = get_event_loop()
    return await loop.run_in_executor(None, call, *args)


def force_update(db_name, elements):
    """ This is only called from external script for db maintenance
    """
    collections[db_name].delete_many({})
    collections[db_name].insert_many(elements)


def update_element(collection, e_id, doc):
    """ Update player p into db
    """
    if collections[collection].count_documents({"_id": e_id}) != 0:
        collections[collection].update_one({"_id": e_id}, {"$set": doc})
    else:
        raise DatabaseError(f"update_element: Element {e_id} doesn't exist in collection {collection}")


def push_element(collection, e_id, doc):
    if collections[collection].count_documents({"_id": e_id}) != 0:
        collections[collection].update_one({"_id": e_id}, {"$push": doc})
    else:
        raise DatabaseError(f"update_element: Element {e_id} doesn't exist in collection {collection}")


def get_element(collection, item_id):
    if collections[collection].count_documents({"_id": item_id}) == 0:
        return
    item = collections[collection].find_one({"_id": item_id})
    return item


def get_specific(collection, e_id, specific):
    if collections[collection].count_documents({"_id": e_id}) == 0:
        return
    item = collections[collection].find_one({"_id": e_id}, {"_id": 0, specific: 1})[specific]
    return item


def set_element(collection, e_id, data):
    if collections[collection].count_documents({"_id": e_id}) != 0:
        collections[collection].replace_one({"_id": e_id}, data)
    else:
        collections[collection].insert_one(data)


def remove_element(collection, e_id):
    if collections[collection].count_documents({"_id": e_id}) != 0:
        collections[collection].delete_one({"_id": e_id})
    else:
        raise DatabaseError(f"Element {e_id} doesn't exist in collection {collection}")
