import modules.config as cfg
import modules.database as db
from modules.tools import AutoDict

import operator

_name_getter_func = None


def init(name_getter_func):
    global _name_getter_func
    _name_getter_func = name_getter_func


def ill_weapons_from_data(data):
    ill_weapons = dict()
    for weap_doc in data:
        ill_weapons[weap_doc["weapon_id"]] = weap_doc["kills"]
    return ill_weapons


def get_ill_weapons_doc(ill_weapons):
    data = list()
    for weapon_id in ill_weapons.keys():
        doc = {"weapon_id": weapon_id,
               "kills": ill_weapons[weapon_id]
               }
        data.append(doc)
    return data



class TeamScore:
    def __init__(self, t_id, match, name, faction):
        self.__id = t_id
        self.__name = name
        self.__faction = faction
        self.__match = match
        self.__kills = 0
        self.__deaths = 0
        self.__net = 0
        self.__score = 0
        self.__cap = 0
        self.__headshots = 0
        self.__players = list()

    @property
    def id(self):
        return self.__id

    @property
    def name(self):
        return self.__name

    @property
    def nb_players(self):
        return len(self.__players)

    @property
    def players(self):
        return self.__players

    @property
    def cap(self):
        return self.__cap

    @property
    def score(self):
        return self.__score

    @property
    def match(self):
        return self.__match

    @property
    def net(self):
        return self.__net

    @property
    def kills(self):
        return self.__kills

    @property
    def deaths(self):
        return self.__deaths

    @property
    def faction(self):
        return self.__faction

    @property
    def hsr(self):
        if self.__kills == 0:
            return 0
        else:
            return self.__headshots / self.__kills

    @property
    def ig_ids_list(self):
        new_list = list()
        for p in self.__players:
            if not p.is_disabled:
                new_list.append(p)
        return ",".join(str(p.ig_id) for p in new_list)

    @classmethod
    def from_data(cls, i, match, data):
        obj = cls(i, match, data["name"], data["faction_id"])
        obj.__faction = data["faction_id"]
        obj.__score = data["score"]
        obj.__net = data["net"]
        obj.__deaths = data["deaths"]
        obj.__kills = data["kills"]
        obj.__cap = data["cap_points"]
        for player in data["players"]:
            obj.add_player(PlayerScore.new_from_data(player, obj))
        for player in obj.players:
            obj.__headshots += player.headshots
        return obj

    def get_data(self):
        data = {"name": self.__name,
                "faction_id": self.__faction,
                "score": self.__score,
                "net": self.__net,
                "deaths": self.__deaths,
                "kills": self.__kills,
                "cap_points": self.__cap,
                "players": [p.get_data() for p in self.__players]
                }
        return data

    def add_player(self, score_player):
        self.__players.append(score_player)

    def reset_score(self):
        self.__score = 0
        self.__net = 0
        self.__deaths = 0
        self.__kills = 0
        self.__headshots = 0
        for p in self.__players:
            p.reset_score()

    def round_update(self, round_no):
        for p in self.__players:
            p.round_update(round_no)

    def add_cap(self, points):
        self.__cap += points
        self.__score += points
        # self.__net += points

    def add_score(self, points):
        self.__score += points

    def add_net(self, points):
        self.__net += points

    def add_one_kill(self, is_hs):
        if is_hs:
            self.__headshots += 1
        self.__kills += 1

    def add_one_death(self):
        self.__deaths += 1


class PlayerScore:
    def __init__(self, p_id, team):
        self.stats = None
        self.__id = p_id
        self.__team = team
        self.__name = "Unknown"
        self.__ig_name = "N/A"
        self.__ig_id = 0
        self.__kills = 0
        self.__deaths = 0
        self.__net = 0
        self.__score = 0
        self.__headshots = 0
        self.__is_disabled = False
        self.__rounds = [False, False]
        self.__illegal_weapons = AutoDict()
        self.__loadouts = dict()

    @classmethod
    def new_from_data(cls, data, team):
        try:
            ig_name = data["ig_name"]
        except KeyError:
            ig_name = "N/A"
        obj = cls(data["discord_id"], team)
        if _name_getter_func:
            obj.__name = _name_getter_func(data["discord_id"])
        obj.__ig_name = ig_name
        obj.__ig_id = data["ig_id"]
        obj.__rounds = data["rounds"]
        if data["loadouts"]:
            for loadout in data["loadouts"]:
                ld = Loadout.new_from_data(obj, loadout)
                obj.__loadouts[ld.id] = ld
                obj.__score += ld.score
                obj.__net += ld.net
                obj.__deaths += ld.deaths
                obj.__kills += ld.kills
                obj.__headshots += ld.headshots
                for weap in ld.ill_weapons.keys():
                    if weap in obj.__illegal_weapons:
                        obj.__illegal_weapons[weap] += ld.ill_weapons[weap]
                    else:
                        obj.__illegal_weapons[weap] = ld.ill_weapons[weap]
        return obj

    def disable(self):
        self.__is_disabled = True

    def enable(self):
        self.__is_disabled = False

    def reset_score(self):
        self.__score = 0
        self.__net = 0
        self.__deaths = 0
        self.__kills = 0
        self.__headshots = 0
        self.__illegal_weapons.clear()
        self.__loadouts.clear()

    def round_update(self, round_num):
        if self.__rounds[round_num]:
            self.enable()
        else:
            self.disable()

    def update(self, name, ig_name, ig_id):
        self.__rounds[self.__team.match.round_no - 1] = True
        self.__name = name
        self.__ig_name = ig_name
        self.__ig_id = ig_id

    def get_main_loadouts(self):
        result = list()
        key = operator.attrgetter("weight")
        sorted_loadouts = sorted(self.__loadouts.values(), key=key, reverse=True)
        if len(sorted_loadouts) > 2:
            sorted_loadouts = sorted_loadouts[:2]
        return [load.name for load in sorted_loadouts]

    def update_stats(self):
        self.stats.add_data(self.team.match.id, self.team.match.round_length*2, self.get_data())

    async def db_update_stats(self):
        self.update_stats()
        await db.async_db_call(db.set_element, "player_stats", self.__id, self.stats.get_data())

    @property
    def match(self):
        return self.__team.match

    @property
    def is_disabled(self):
        return self.__is_disabled

    @property
    def mention(self):
        return f"<@{self.__id}>"

    @property
    def name(self):
        return self.__name

    @property
    def id(self):
        return self.__id

    @property
    def ig_id(self):
        return self.__ig_id

    @property
    def ig_name(self):
        return self.__ig_name

    @property
    def score(self):
        return self.__score

    @property
    def net(self):
        return self.__net

    @property
    def kills(self):
        return self.__kills

    @property
    def deaths(self):
        return self.__deaths

    @property
    def team(self):
        return self.__team

    @property
    def loadouts(self):
        return self.__loadouts

    @property
    def headshots(self):
        return self.__headshots

    @property
    def hsr(self):
        if self.__kills == 0:
            return 0
        else:
            return self.__headshots / self.__kills

    def get_data(self):
        data = {"discord_id": self.__id,
                "ig_id": self.__ig_id,
                "ig_name": self.__ig_name,
                "rounds": self.__rounds,
                "loadouts": [loadout.get_data() for loadout in self.__loadouts.values()]
                }
        return data

    def get_loadout(self, l_id):
        if l_id not in self.__loadouts:
            self.__loadouts[l_id] = Loadout(l_id, self)
        loadout = self.__loadouts[l_id]
        loadout.add_weight()
        return loadout

    def add_one_death(self):
        self.__deaths += 1
        self.__team.add_one_death()

    def add_one_kill(self, is_hs):
        if is_hs:
            self.__headshots += 1
        self.__kills += 1
        self.__team.add_one_kill(is_hs)

    def add_score(self, points):
        self.__score += points
        self.__team.add_score(points)

    def add_net(self, points):
        self.__net += points
        self.__team.add_net(points)

    def add_illegal_weapon(self, weap_id):
        self.__illegal_weapons.auto_add(weap_id, 1)


class Loadout:
    def __init__(self, l_id, p_score):
        self.__id = l_id
        self.__player_score = p_score
        self.__name = cfg.loadout_id[l_id]
        self.__faction = p_score.team.faction
        self.__kills = 0
        self.__deaths = 0
        self.__score = 0
        self.__net = 0
        self.__headshots = 0
        self.__illegal_weapons = AutoDict()
        self.__weight = 0

    @property
    def id(self):
        return self.__id

    @property
    def player_score(self):
        return self.__player_score

    @property
    def name(self):
        return self.__name

    @property
    def faction(self):
        return self.__faction

    @property
    def weight(self):
        return self.__weight

    @property
    def score(self):
        return self.__score

    @property
    def net(self):
        return self.__net

    @property
    def kills(self):
        return self.__kills

    @property
    def deaths(self):
        return self.__deaths

    @property
    def ill_weapons(self):
        return self.__illegal_weapons

    @property
    def headshots(self):
        return self.__headshots

    @classmethod
    def new_from_data(cls, p_score, data):
        obj = cls(data["loadout_id"], p_score)
        obj.__score = data["score"]
        obj.__net = data["net"]
        obj.__deaths = data["deaths"]
        obj.__kills = data["kills"]
        obj.__weight = data["weight"]
        obj.__headshots = data["headshots"]
        obj.__illegal_weapons = ill_weapons_from_data(data["ill_weapons"])
        return obj

    def get_data(self):
        data = {"loadout_id": self.__id,
                "score": self.__score,
                "net": self.__net,
                "deaths": self.__deaths,
                "kills": self.__kills,
                "weight": self.__weight,
                "headshots": self.__headshots,
                "ill_weapons": get_ill_weapons_doc(self.__illegal_weapons)
                }
        return data

    def add_weight(self):
        self.__weight += 1

    def add_illegal_weapon(self, weap_id):
        self.__player_score.add_illegal_weapon(weap_id)
        self.__illegal_weapons.auto_add(weap_id, 1)

    def add_one_kill(self, points, is_hs):
        if is_hs:
            self.__headshots += 1
        self.__kills += 1
        self.__player_score.add_one_kill(is_hs)
        self.__add_points(points)

    def add_one_death(self, points):
        self.__deaths += 1
        self.__player_score.add_one_death()
        points = -points
        self.__net += points
        self.__player_score.add_net(points)

    def add_one_tk(self):
        self.__add_points(cfg.scores["teamkill"])

    def add_one_suicide(self):
        self.__deaths += 1
        self.__player_score.add_one_death()
        self.__add_points(cfg.scores["suicide"])

    def __add_points(self, points):
        self.__net += points
        self.__score += points
        self.__player_score.add_score(points)
        self.__player_score.add_net(points)
