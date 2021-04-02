import modules.database as db


class PlayerStat:
    def __init__(self, p_id, data=None):
        self.id = p_id
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

    @classmethod
    async def get_from_database(cls, p_id):
        dta = await db.async_db_call(db.get_element, "player_stats", p_id)
        return cls(p_id, dta)

    def add_data(self, match_id, dta):
        self.matches.append(match_id)
        self.kills += dta["kills"]
        self.deaths += dta["deaths"]
        self.net += dta["net"]
        self.score += dta["score"]

    def add_stats(self, a_player):
        self.matches.append(a_player.match.id)
        self.kills += a_player.kills
        self.deaths += a_player.deaths
        self.net += a_player.net
        self.score += a_player.score

    def get_data(self):
        dta = dict()
        dta["_id"] = self.id
        dta["matches"] = self.matches
        dta["kills"] = self.kills
        dta["deaths"] = self.deaths
        dta["net"] = self.net
        dta["score"] = self.score
        return dta