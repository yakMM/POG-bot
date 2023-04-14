from classes import Player, PlayerStat
import asyncio
import os
import operator
import statistics
import numpy as np
import modules.tools as tools
from match.classes import Match
from classes import Player
from datetime import datetime as dt

import modules.config as cfg
import modules.database as db


if os.path.isfile("test"):
    LAUNCHSTR = "_test"
else:
    LAUNCHSTR = ""

cfg.get_config("")
db.init(cfg.database)

db.get_all_elements(Player.new_from_data, "users")


def get_all_stats():
    all_stats = list()

    def from_data(dta):
        p = Player.get(dta["_id"])
        if p:
            name = p.name
        else:
            name = "N/A"
        stat_p = PlayerStat(dta["_id"], name=name, data=dta)
        if stat_p.nb_matches_played > 1:
            all_stats.append(stat_p)

    db.get_all_elements(from_data, "player_stats")

    print("Highest Kills per match:")
    key = operator.attrgetter("kpm")
    sorted_stats = sorted(all_stats, key=key, reverse=True)
    for s in sorted_stats[:5]:
        print(f"id: [{s.id}], name: [{s.name}], nb_matches: [{s.nb_matches_played}], value: [{s.kpm}]")

    print("Highest Number of matches played, top 5:")
    key = operator.attrgetter("nb_matches_played")
    sorted_stats = sorted(all_stats, key=key, reverse=True)
    for s in sorted_stats[:5]:
        print(f"id: [{s.id}], name: [{s.name}], nb_matches: [{s.nb_matches_played}], value: [{s.nb_matches_played}]")

    print("Highest Number of times captain, top 5:")
    key = operator.attrgetter("times_captain")
    sorted_stats = sorted(all_stats, key=key, reverse=True)
    for s in sorted_stats[:5]:
        print(f"id: [{s.id}], name: [{s.name}], nb_matches: [{s.nb_matches_played}], value: [{s.times_captain}]")

    print("Highest ratio of captain / match, top 10:")
    key = operator.attrgetter("cpm")
    sorted_stats = sorted(all_stats, key=key, reverse=True)
    for s in sorted_stats[:10]:
        print(f"id: [{s.id}], name: [{s.name}], nb_matches: [{s.nb_matches_played}], value: [{s.cpm}]")


_all_db_matches = list()


class DbMatch:
    @classmethod
    def new_from_data(cls, data):
        obj = cls(data)
        _all_db_matches.append(obj)

    def __init__(self, data):
        self.data = data
        self.id = data["_id"]
        self.match = Match(data=data)

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


class NetScore:
    def __init__(self, id, value, match_id):
        self.player = Player.get(id)
        self.value = value
        self.match = match_id


def get_best_net():
    players = list()
    db.get_all_elements(DbMatch.new_from_data, "matches")
    for m in _all_db_matches:
        if m.match.data.round_length > 10:
            print("skipping 15 min")
            continue
        invalid = False
        for tm in m.match.data.teams:
            for p in tm.players:
                if p.net == 0 and p.kills == 0 and p.deaths == 0:
                    print("skipping invalid")
                    invalid = True
                    break
            if invalid:
                break
        if invalid:
            continue

        # if abs(m.match.data.teams[0].score - m.match.data.teams[1].score) > 30:
        #     continue

        for tm in m.match.data.teams:
            for p in tm.players:
                n = NetScore(p.id, p.net, m.match.id)
                players.append(n)
                # if p.id not in players:
                #     players[p.id] = n
                # elif p.kills > players[p.id].value:
                #     players[p.id] = n

    srt = sorted(players, key=operator.attrgetter("value"), reverse=True)
    for i, s in enumerate(srt[:50]):
        print(f"{i}: Player `{s.player.name}` [`{s.player.id}`, in match `{s.match}`, NET: `{s.value}`]")


def get_match_stats_2(begin, end):
    db.get_all_elements(DbMatch.new_from_data, "matches")
    matches = list()
    players = tools.AutoDict()
    for m in _all_db_matches:
        mdta = m.match.data
        if begin.timestamp() <= mdta.round_stamps[0] <= end.timestamp():
            matches.append(mdta)
            for team in mdta.teams:
                for player in team.players:
                    players.auto_add(player.id, 1)
    players = {k: v for k, v in sorted(players.items(), key=lambda item: item[1])}
    for k, v in players.items():
        print(f"Id `{k}` name `{Player.get(k).name}` => {v} matches")



# get_match_stats_2(begin=dt(year=2022, month=7, day=9), end=dt(year=2022, month=11, day=10))
get_best_net()
