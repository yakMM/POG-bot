
class Weapon:
    _all_weapons = dict()

    @classmethod
    def get(cls, w_id):
        return cls._all_weapons.get(w_id)

    @classmethod
    def clear_all(cls):
        cls._all_weapons.clear()

    def __init__(self, data):
        self.__id = data["_id"]
        self.__name = data["name"]
        self.__cat_id = data["cat_id"]
        self.__points = data["points"]
        self.__banned = data["banned"]
        self.__faction = data["faction"]
        Weapon._all_weapons[self.__id] = self

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
