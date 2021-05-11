from classes import Player, PlayerStat
import asyncio
import os
import operator
import statistics
import numpy as np


import modules.config as cfg
import modules.database as db


if os.path.isfile("test"):
    LAUNCHSTR = "_test"
else:
    LAUNCHSTR = ""
cfg.get_config(LAUNCHSTR)
db.init(cfg.database)

db.get_all_elements(Player.new_from_data, "users")


all_stats = list()
for p in Player.get_all_players_list():
    loop = asyncio.get_event_loop()
    stat_player = loop.run_until_complete(PlayerStat.get_from_database(p.id, p.name))
    all_stats.append(stat_player)

print("Highest Kills per match:")
key = operator.attrgetter("kpm")
sorted_stats = sorted(all_stats, key=key, reverse=True)
for s in sorted_stats[:5]:
    print(f"id: [{s.id}], name: [{s.name}], nb_match: [{s.nb_matches_played}], value: [{s.kpm}]")

print("Highest Number of matches played, top 5:")
key = operator.attrgetter("nb_matches_played")
sorted_stats = sorted(all_stats, key=key, reverse=True)
for s in sorted_stats[:5]:
    print(f"id: [{s.id}], name: [{s.name}], value: [{s.nb_matches_played}]")


_all_db_matches = list()


class DbMatch:
    @classmethod
    def new_from_data(cls, data):
        obj = cls(data)
        _all_db_matches.append(obj)

    def __init__(self, data):
        self.data = data
        self.id = data["_id"]

    @property
    def launch(self):
        return self.data["match_launching"]

    @property
    def start(self):
        return self.data["rounds"][0]["timestamp"]


def get_match_stats():
    teams_scores = [0, 0]
    win_nb = [0, 0]
    db.get_all_elements(DbMatch.new_from_data, "matches")
    for m in _all_db_matches:
        t0 = m.data["teams"][0]["score"]
        t1 = m.data["teams"][1]["score"]
        teams_scores[0] += t0
        teams_scores[1] += t1
        if t1 >= t0:
            win_nb[1] += 1
        else:
            win_nb[0] += 1

    print(teams_scores)
    print(win_nb)

def get_match_logs():
    db.get_all_elements(DbMatch.new_from_data, "match_logs")
    average = list()
    for m in _all_db_matches:
        try:
            average.append(m.start - m.launch)
        except KeyError:
            pass
    print(f"mean: {statistics.mean(average)}")
    print(f"median: {statistics.median(average)}")
    std = np.std(average)
    print(statistics.quantiles(average))
    print(std)


get_match_logs()
