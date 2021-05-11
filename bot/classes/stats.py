import modules.database as db
import modules.config as cfg
import modules.tools as tools
import operator


class PlayerStat:
    def __init__(self, p_id, name, data=None):
        self.id = p_id
        self.name = name
        if data:
            self.matches = data["matches"]
            self.time_played = data["time_played"]
            self.loadouts = dict()
            for l_data in data["loadouts"]:
                l_id = l_data["id"]
                self.loadouts[l_id] = LoadoutStats(l_id, l_data)
        else:
            self.matches = list()
            self.time_played = 0
            self.loadouts = dict()

    @property
    def nb_matches_played(self):
        return len(self.matches)

    @property
    def kills_per_match(self):
        return self.kpm * cfg.general["round_length"] * 2

    @property
    def kpm(self):
        if self.time_played == 0:
            return 0
        return self.kills / self.time_played

    @property
    def score(self):
        score = 0
        for loadout in self.loadouts.values():
            score += loadout.score
        return score

    @property
    def kills(self):
        kills = 0
        for loadout in self.loadouts.values():
            kills += loadout.kills
        return kills

    @property
    def deaths(self):
        deaths = 0
        for loadout in self.loadouts.values():
            deaths += loadout.deaths
        return deaths

    @property
    def net(self):
        net = 0
        for loadout in self.loadouts.values():
            net += loadout.score
        return net

    @property
    def most_played_loadout(self):
        l_dict = tools.AutoDict()
        for loadout in self.loadouts.values():
            l_name = cfg.loadout_id[loadout.id]
            l_dict.auto_add(l_name, loadout.weight)
        try:
            name = sorted(l_dict.items(), key=operator.itemgetter(1), reverse=True)[0][0]
            n_l = name.split('_')
            for i in range(len(n_l)):
                n_l[i] = n_l[i][0].upper() + n_l[i][1:]
            name = " ".join(n_l)
        except IndexError:
            name = "None"

        return name

    @property
    def mention(self):
        return f"<@{self.id}>"

    @classmethod
    async def get_from_database(cls, p_id, name):
        dta = await db.async_db_call(db.get_element, "player_stats", p_id)
        return cls(p_id, name=name, data=dta)

    def add_data(self, match_id, time_played, dta):
        self.matches.append(match_id)
        self.time_played += time_played
        for l_data in dta["loadouts"]:
            l_id = l_data["loadout_id"]
            if l_id in self.loadouts:
                self.loadouts[l_id].add_data(l_data)
            else:
                self.loadouts[l_id] = LoadoutStats(l_id, l_data)

    def get_data(self):
        dta = dict()
        dta["_id"] = self.id
        dta["matches"] = self.matches
        dta["time_played"] = self.time_played
        dta["loadouts"] = [loadout.get_data() for loadout in self.loadouts.values()]
        return dta


class LoadoutStats:
    def __init__(self, l_id, data=None):
        self.id = l_id
        if data:
            self.weight = data["weight"]
            self.kills = data["kills"]
            self.deaths = data["deaths"]
            self.net = data["net"]
            self.score = data["score"]
        else:
            self.weight = 0
            self.kills = 0
            self.deaths = 0
            self.net = 0
            self.score = 0

    def add_data(self, dta):
        self.weight += dta["weight"]
        self.kills += dta["kills"]
        self.deaths += dta["deaths"]
        self.net += dta["net"]
        self.score += dta["score"]

    def get_data(self):
        data = {"id": self.id,
                "score": self.score,
                "net": self.net,
                "deaths": self.deaths,
                "kills": self.kills,
                "weight": self.weight,
                }
        return data
