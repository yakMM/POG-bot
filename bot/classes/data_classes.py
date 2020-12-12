class DataPlayer:
    def __init__(self, dta, team):
        try:
            self.ig_name = dta["ig_name"]
        except KeyError:
            self.ig_name = "N/A"
        self.ig_id = dta["ig_id"]
        self.id = dta["discord_id"]
        self.team = team
        self.score = dta["score"]
        self.net = dta["net"]
        self.deaths = dta["deaths"]
        self.kills = dta["kills"]
        self.rank = dta["rank"]
        self.ill_weapons = dta["ill_weapons"]
