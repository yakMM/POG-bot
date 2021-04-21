from classes import Player, PlayerStat
import asyncio
import os
import operator

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


def kpm_key(st_p):
    if st_p.nb_matches_played > 0:
        return st_p.kills / st_p.nb_matches_played
    else:
        return 0


print("Highest Kills per match:")
sorted_stats = sorted(all_stats, key=kpm_key, reverse=True)
for s in sorted_stats[:5]:
    print(f"id: [{s.id}], name: [{s.name}], nb_match: [{s.nb_matches_played}], value: [{s.kpm}]")

print("Highest Number of matches played, top 5:")
key = operator.attrgetter("nb_matches_played")
sorted_stats = sorted(all_stats, key=key, reverse=True)
for s in sorted_stats[:5]:
    print(f"id: [{s.id}], name: [{s.name}], value: [{s.nb_matches_played}]")



