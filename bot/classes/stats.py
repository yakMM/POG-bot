import modules.database as db


class PlayerStat:
    def __init__(self, p_id, name, data=None):
        self.id = p_id
        self.name = name
        if data:
            self.matches = data["matches"]
            self.kills = data["kills"]
            self.deaths = data["deaths"]
            self.net = data["net"]
            self.score = data["score"]
        else:
            self.matches = list()
            self.kills = 0
            self.deaths = 0
            self.net = 0
            self.score = 0

    @property
    def nb_matches_played(self):
        return len(self.matches)

    @property
    def mention(self):
        return f"<@{self.id}>"

    @classmethod
    async def get_from_database(cls, p_id, name):
        dta = await db.async_db_call(db.get_element, "player_stats", p_id)
        return cls(p_id, name=name, data=dta)

    def add_data(self, match_id, dta):
        self.matches.append(match_id)
        self.kills += dta["kills"]
        self.deaths += dta["deaths"]
        self.net += dta["net"]
        self.score += dta["score"]

    def add_stats(self, player):
        self.matches.append(player.match.id)
        self.kills += player.kills
        self.deaths += player.deaths
        self.net += player.net
        self.score += player.score

    def get_data(self):
        dta = dict()
        dta["_id"] = self.id
        dta["matches"] = self.matches
        dta["kills"] = self.kills
        dta["deaths"] = self.deaths
        dta["net"] = self.net
        dta["score"] = self.score
        return dta