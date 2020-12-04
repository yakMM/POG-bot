# @CHECK 2.0 features OK

from modules.exceptions import ElementNotFound

_all_weapons = dict()


def get_weapon(id):
    we = _all_weapons.get(id)
    if we is None:
        raise ElementNotFound(id)
    return we


class Weapon:
    def __init__(self, data):
        self.__id = data["_id"]
        self.__name = data["name"]
        self.__cat_id = data["cat_id"]
        self.__points = data["points"]
        self.__banned = data["banned"]
        self.__faction = data["faction"]
        _all_weapons[self.__id] = self

    def get_data(self):  # get data for database push
        data = {"_id": self.__id,
                "name": self.__name,
                "cat_id": self.__cat_id,
                "points": self.__points,
                "banned": self.__banned,
                "faction": self.__faction
                }
        return data

    @property
    def id(self):
        return self.__id
    
    @property
    def name(self):
        return self.__name

    @property
    def is_banned(self):
        return self.__banned
    
    @property
    def points(self):
        return self.__points
