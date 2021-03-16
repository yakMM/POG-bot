""" Contains list of all possible bases
    Contains base selection object when searching for a base
"""

import modules.config as cfg
from general.exceptions import ElementNotFound


from logging import getLogger


log = getLogger("pog_bot")

MAX_SELECTED = 15


class Base:
    _all_bases_list = list()
    _base_pool = list()

    @classmethod
    def get(cls, m_id: int):
        if m_id not in cls._all_bases_list:
            raise ElementNotFound(m_id)
        return cls._all_bases_list[m_id]

    @classmethod
    def get_bases_from_name(cls, name, base_pool=False):
        results = list()
        for base in (cls._base_pool if base_pool else cls._all_bases_list):
            if name.lower() in base.name.lower():
                results.append(base)
        return results

    @classmethod
    def get_base_from_id(cls, base_id):
        for base in cls._all_bases_list:
            if base.id == base_id:
                return base

    @classmethod
    def get_bases(cls):
        return cls._all_bases_list.copy()

    @classmethod
    def get_pool(cls):
        return cls._base_pool.copy()

    def __init__(self, data):
        self.__id = data["_id"]
        self.__name = data["name"]
        self.__zone_id = data["zone_id"]
        self.__type_id = data["type_id"]
        self.__in_pool = data["in_map_pool"]
        if self.__in_pool:
            Base._base_pool.append(self)
        Base._all_bases_list.append(self)

    def get_data(self):  # get data for database push
        data = {"_id": self.__id,
                "name": self.__name,
                "zone_id": self.__zone_id,
                "type_id": self.__type_id,
                "in_base_pool": self.__in_pool
                }
        return data

    @property
    def pool(self):
        return self.__in_pool

    @pool.setter
    def pool(self, bl):
        self.__in_pool = bl

    @property
    def id(self):
        return self.__id

    @property
    def name(self):
        name = self.__name
        if self.__type_id in cfg.facility_suffix:
            name += f" {cfg.facility_suffix[self.__type_id]}"
        return name