class PlayerStat:
    def __init__(self, d_id):
        self.discord_id = d_id
        self.matches = list()
        self.kills = 0
        self.deaths = 0
        self.net = 0
        self.score = 0

    def add_data(self, match_id, dta):
        self.matches.append(match_id)
        self.kills += dta["kills"]
        self.deaths += dta["deaths"]
        self.net += dta["net"]
        self.score += dta["score"]

    def get_data(self):
        dta = dict()
        dta["_id"] = self.discord_id
        dta["matches"] = self.matches
        dta["kills"] = self.kills
        dta["deaths"] = self.deaths
        dta["net"] = self.net
        dta["score"] = self.score
        return dta