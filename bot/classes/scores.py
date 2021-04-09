import modules.config as cfg
import modules.database as db


def ill_weapons_from_data(data):
    ill_weapons = dict()
    for weap_doc in data:
        ill_weapons[weap_doc["weap_id"]] = weap_doc["kills"]
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
    def __init__(self, id, match, name, faction):
        self.__id = id
        self.__name = name
        self.__faction = faction
        self.__match = match
        self.__kills = 0
        self.__deaths = 0
        self.__net = 0
        self.__score = 0
        self.__cap = 0
        self.__players = list()

    @property
    def id(self):
        return self.__id

    @property
    def name(self):
        return self.__name

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

    @classmethod
    def from_data(cls, match, i, data):
        obj = cls(i, match, data["name"], data["faction_id"])
        obj.__faction = data["faction_id"]
        obj.__score = data["score"]
        obj.__net = data["net"]
        obj.__deaths = data["deaths"]
        obj.__kills = data["kills"]
        obj.__cap = data["cap_points"]
        for player in data["players"]:
            obj.add_player(PlayerScore.new_from_data(player, obj))

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

    def add_cap(self, points):
        self.__cap += points
        self.__score += points
        # self.__net += points

    def add_score(self, points):
        self.__score += points

    def add_net(self, points):
        self.__net += points

    def add_one_kill(self):
        self.__kills += 1

    def add_one_death(self):
        self.__deaths += 1


class PlayerScore:
    def __init__(self, p_id, team, name, ig_name, ig_id):
        self.stats = None
        self.__id = p_id
        self.__team = team
        self.__name = name
        self.__ig_name = ig_name
        self.__ig_id = ig_id
        self.__kills = 0
        self.__deaths = 0
        self.__net = 0
        self.__score = 0
        self.__illegal_weapons = dict()
        self.__loadouts = dict()

    @classmethod
    def new_from_data(cls, data, team, name="N/A"):
        try:
            ig_name = data["ig_name"]
        except KeyError:
            ig_name = "N/A"
        obj = cls(data["discord_id"], team, name, ig_name, data["ig_id"])
        if data["loadouts"]:
            for loadout in data["loadouts"]:
                ld = Loadout.new_from_data(obj, loadout)
                obj.__loadouts[ld.id] = ld
                obj.__score += ld.score
                obj.__net += ld.net
                obj.__deaths += ld.deaths
                obj.__kills += ld.kills
                for weap in ld.ill_weapons.keys():
                    if weap in obj.__illegal_weapons:
                        obj.__illegal_weapons[weap] += obj.__illegal_weapons[weap]
                    else:
                        obj.__illegal_weapons[weap] = obj.__illegal_weapons[weap]
        return obj

    def get_main_loadouts(self):
        result = list()
        all = list(self.__loadouts.values())
        for i in range(2):
            max_v = 0
            max_l = None
            for ld in all:
                if ld.weight > max_v:
                    max_l = ld
            if max_l:
                result.append(max_l.name)
                all.remove(max_l)
            else:
                return result
        return result

    async def update_stats(self):
        self.stats.add_stats(self)
        await db.async_db_call(db.set_element, "player_stats", self.__id, self.stats.get_data())

    @property
    def match(self):
        return self.__team.match

    @property
    def mention(self):
        return f"<@{self.__id}>"

    @property
    def name(self):
        return self.__name

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

    def get_data(self):
        data = {"discord_id": self.__id,
                "ig_id": self.__ig_id,
                "ig_name": self.__ig_name,
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

    def add_one_kill(self):
        self.__kills += 1
        self.__team.add_one_kill()

    def add_score(self, points):
        self.__score += points
        self.__team.add_score(points)

    def add_net(self, points):
        self.__net += points
        self.__team.add_net(points)

    def add_illegal_weapon(self, weap_id):
        if weap_id in self.__illegal_weapons:
            self.__illegal_weapons[weap_id] += 1
        else:
            self.__illegal_weapons[weap_id] = 1

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
        self.__illegal_weapons = dict()
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

    @classmethod
    def new_from_data(cls, p_score, data):
        obj = cls(data["loadout_id"], p_score)
        obj.__score = data["net"]
        obj.__net = data["net"]
        obj.__deaths = data["deaths"]
        obj.__kills = data["kills"]
        obj.__weight = data["weight"]
        obj.__illegal_weapons = ill_weapons_from_data(data["ill_weapons"])
        return obj

    def get_data(self):
        data = {"loadout_id": self.__id,
                "score": self.__score,
                "net": self.__net,
                "deaths": self.__deaths,
                "kills": self.__kills,
                "weight": self.__weight,
                "ill_weapons": get_ill_weapons_doc(self.__illegal_weapons)
                }
        return data

    def add_weight(self):
        self.__weight += 1

    def add_illegal_weapon(self, weap_id):
        self.__player_score.add_illegal_weapon(weap_id)
        if weap_id in self.__illegal_weapons:
            self.__illegal_weapons[weap_id] += 1
        else:
            self.__illegal_weapons[weap_id] = 1

    def add_one_kill(self, points):
        self.__kills += 1
        self.__player_score.add_one_kill()
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


    # def add_loadout_event(self, loadout):
    #     if loadout in self.__loadouts:
    #         self.__loadouts[loadout] += 1
    #     else:
    #         self.__loadouts[loadout] = 1
    #
    # def get_main_loadouts(self):
    #     max2_v = 0
    #     max2_k = 0
    #     max_v = 0
    #     max_k = 0
    #     for k in self.__loadouts.keys():
    #         if self.__loadouts[k] > max_v:
    #             max2_k = max_k
    #             max2_v = max_v
    #             max_v = self.__loadouts[k]
    #             max_k = k
    #     return max_k, max2_k
    #
    # def get_loadouts(self):
    #     loadouts = list()
    #     for k in self.__loadouts.keys():
    #         try:
    #             loadouts.append(cfg.loadout_id[k])
    #         except KeyError:
    #             pass
    #     return loadouts
    #
    # def get_data(self):
    #     data = {"discord_id": self.__player.id,
    #             "ig_id": self.ig_id,
    #             "ig_name": self.ig_name,
    #             "ill_weapons": self.__get_ill_weaponsDoc(),
    #             "loadouts": self.__loadouts,
    #             "score": self.__score,
    #             "net": self.__net,
    #             "deaths": self.__deaths,
    #             "kills": self.__kills,
    #             }
    #     return data