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
            self.matches_won = data["match_stats"]["nb_won"]
            self.matches_lost = data["match_stats"]["nb_lost"]
            self.time_played = data["time_played"]
            self.times_captain = data["times_captain"]
            self.pick_order = tools.AutoDict(data["pick_order"])
            self.loadouts = dict()
            for l_data in data["loadouts"]:
                l_id = l_data["id"]
                self.loadouts[l_id] = LoadoutStats(l_id, l_data)
        else:
            self.matches = list()
            self.matches_won = 0
            self.matches_lost = 0
            self.time_played = 0
            self.times_captain = 0
            self.pick_order = tools.AutoDict()
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
    def cpm(self):
        if self.nb_matches_played < 10:
            return 0
        return self.times_captain / self.nb_matches_played

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

    def add_data(self, match_id: int, time_played, player_score):
        self.matches.append(match_id)
        if player_score.team.won_match:
            self.matches_won += 1
        else:
            self.matches_lost += 1
        self.time_played += time_played
        self.times_captain += int(player_score.is_captain)
        self.pick_order.auto_add(str(player_score.pick_index), 1)
        for l_id in player_score.loadouts.keys():
            loadout = player_score.loadouts[l_id]
            if l_id in self.loadouts:
                self.loadouts[l_id].add_data(loadout)
            else:
                self.loadouts[l_id] = LoadoutStats(l_id, loadout.get_data())

    def get_data(self):
        dta = dict()
        dta["_id"] = self.id
        dta["matches"] = self.matches
        dta["match_stats"] = {
            "nb_won": self.matches_won,
            "nb_lost": self.matches_lost,
        }
        dta["time_played"] = self.time_played
        dta["times_captain"] = self.times_captain
        dta["pick_order"] = self.pick_order
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

    def add_data(self, loadout):
        self.weight += loadout.weight
        self.kills += loadout.kills
        self.deaths += loadout.deaths
        self.net += loadout.net
        self.score += loadout.score

    def get_data(self):
        data = {"id": self.id,
                "score": self.score,
                "net": self.net,
                "deaths": self.deaths,
                "kills": self.kills,
                "weight": self.weight,
                }
        return data
