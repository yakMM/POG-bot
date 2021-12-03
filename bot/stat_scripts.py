from classes import Player, PlayerStat
import asyncio
import os
import operator
import statistics
import numpy as np
import modules.tools as tools
from match.classes import Match
from classes import Player

import modules.config as cfg
import modules.database as db


if os.path.isfile("test"):
    LAUNCHSTR = "_test"
else:
    LAUNCHSTR = ""
cfg.get_config(LAUNCHSTR)
db.init(cfg.database)

db.get_all_elements(Player.new_from_data, "users")

def get_all_stats():
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

    print("Highest Number of times captain, top 5:")
    key = operator.attrgetter("times_captain")
    sorted_stats = sorted(all_stats, key=key, reverse=True)
    for s in sorted_stats[:5]:
        print(f"id: [{s.id}], name: [{s.name}], value: [{s.times_captain}]")

    print("Highest ratio of captain / match, top 10:")
    key = operator.attrgetter("cpm")
    sorted_stats = sorted(all_stats, key=key, reverse=True)
    for s in sorted_stats[:10]:
        print(f"id: [{s.id}], name: [{s.name}], value: [{s.cpm}]")


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
    def __init__(self, id, net, match_id):
        self.player = Player.get(id)
        self.net = net
        self.match = match_id

def get_best_net():
    players = dict()
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

        if abs(m.match.data.teams[0].score - m.match.data.teams[1].score) > 30:
            continue

        for tm in m.match.data.teams:
            for p in tm.players:
                n = NetScore(p.id, p.kills, m.match.id)
                if p.id not in players:
                    players[p.id] = n
                elif p.kills > players[p.id].net:
                    players[p.id] = n

    p_list = list(players.values())
    srt = sorted(p_list, key=operator.attrgetter("net"), reverse=True)
    for s in srt[:15]:
        print(f"Player {s.player.name} [{s.player.id}, in match {s.match}, kills: {s.net}]")


get_all_stats()
