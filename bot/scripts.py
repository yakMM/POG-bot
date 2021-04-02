# @CHECK 2.0 features OK

from gspread import service_account
from numpy import array
import modules.config as cfg
from classes import Player, Base
from match.classes.match import Match
import requests
import json
import asyncio
from classes.weapons import Weapon
import os
from datetime import datetime as dt

from classes.stats import PlayerStat
import modules.database as db
import modules.accounts_handler as accounts
from random import choice as random_choice
import modules.tools as tools
from modules.image_maker import _make_image

import modules.census as census

if os.path.isfile("test"):
    LAUNCHSTR = "_test"
else:
    LAUNCHSTR = ""
cfg.get_config(LAUNCHSTR)
db.init(cfg.database)
#db.get_all_elements(Player.new_from_data, "users")
db.get_all_elements(Base, "static_bases")
db.get_all_elements(Weapon, "static_weapons")

_match_played_dict = dict()

class DbPlayer(Player):
    @classmethod
    def new_from_data(cls, data):
        new_data = dict()
        new_data["name"] = data["name"]
        new_data["_id"] = data["_id"]
        new_data["notify"] = data["notify"]
        if data["timeout"]["time"] != 0:
            new_data["timeout"] = data["timeout"]["time"]
        new_data["is_registered"] = True
        if data["has_own_account"]:
            new_data["ig_names"] = data["ig_names"]
            new_data["ig_ids"] = data["ig_ids"]
        super().new_from_data(new_data)

_all_db_matches = list()
convert_dict_1 = dict()
convert_dict_2 = dict()

class DbMatch:
    @classmethod
    def new_from_data(cls, data):
        obj = cls(data)
        _all_db_matches.append(obj)

    def __init__(self, data):
        self.data = data
        self.id = data["_id"]

    def repair_field(self):
        if "cfg.general['round_length']_min" in self.data:
            print(f"Wrong match {self.data['_id']}")
            self.data["round_length"] = self.data["cfg.general['round_length']_min"]
            del self.data["cfg.general['round_length']_min"]


    def get_played_time(self):
        time = dt.utcfromtimestamp(self.data["round_stamps"][0])
        var = (time.hour + time.minute/60.0 + 14) % 24
        for tm in self.data["teams"]:
            for p in tm["players"]:
                if p["discord_id"] in _match_played_dict:
                    _match_played_dict[p["discord_id"]].append(var)
                else:
                    _match_played_dict[p["discord_id"]] = [var]


    def do_change(self):
        dt = self.data
        for tm in dt["teams"]:
            for p in tm["players"]:
                try:
                    i_id = p["ig_id"]
                except KeyError:
                    i_name = p["ig_name"]
                    print(f"Couldn't find id for name {i_name}")
                    if i_name in convert_dict_2:
                        i_id = convert_dict_2[i_name]
                    else:
                        url = f"http://census.daybreakgames.com/s:{cfg.general['api_key']}/get/ps2:v2/character/?name.first={i_name}&c:show=character_id"
                        jdata = json.loads(requests.get(url).content)
                        i_id = int(jdata["character_list"][0]["character_id"])
                        convert_dict_2[i_name] = i_id
                    p["ig_id"] = i_id
                try:
                    i_name = p["ig_name"]
                except KeyError:
                    print(f"Couldn't find name for id {i_id}")
                    if i_id in convert_dict_1:
                        name = convert_dict_1[i_id]
                    else:
                        url = 'http://census.daybreakgames.com/s:' + \
                        cfg.general['api_key']+'/get/ps2:v2/character/?character_id=' + str(i_id) + \
                        "&c:show=name.first"
                        jdata = json.loads(requests.get(url).content)
                        try:
                            name = jdata["character_list"][0]["name"]["first"]
                        except IndexError:
                            print(f"Error: match {dt['_id']} {i_id}")
                            continue
                        convert_dict_1[i_id] = name
                    p["ig_name"] = name


def get_Accounts():

    gc = service_account(filename=f'google_api_secret{LAUNCHSTR}.json')
    sh = gc.open_by_key(cfg.database["accounts"])
    raw_sheet = sh.worksheet("1")
    sheet_tab = array(raw_sheet.get_all_values())

    num_accounts = sheet_tab.shape[0] - accounts.Y_OFFSET

    accs = list()

    # Get all accounts
    for i in range(num_accounts):
        accs.append(sheet_tab[i + accounts.Y_OFFSET][accounts.X_OFFSET])

    return accs

def push_accounts_to_usage():
    accs = get_Accounts()
    for acc in accs:
        dta = dict()
        dta["_id"] = int(acc)
        dta["usages"] = list()
        dta["unique_usages"] = list()
        db.set_element("accounts_usage", int(acc), dta)


def push2():
    from test2 import id3s
    t=tools.timestamp_now()
    for id in id3s:
        db.push_element("accounts_usage", 7, {"unique_usages": id})
    for e in range(50):
        dta = dict()
        dta["id"] = random_choice(id3s)
        dta["time_start"] = t - (50-e)*5000
        dta["time_stop"] = dta["time_start"] + 200
        dta["match_id"] = 1000-e
        db.push_element("accounts_usage", 7, {"usages": dta})


def push_accounts_to_users():
    accs = get_Accounts()
    loop = asyncio.get_event_loop()
    p_list = list()

    for acc in accs:
        p = Player(int(acc), f"_POG_ACC_{acc}")
        p_list.append(p)
        print(acc)
        char_list = [f"POGx{acc}VS", f"POGx{acc}TR", f"POGx{acc}NC"]
        p.__has_own_account = True
        p.__is_registered = True
        loop.run_until_complete(p._add_characters(char_list))
        db.set_element("users", p.id, p.get_data())
    loop.close()


def get_all_bases_from_api():
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2/map_region/?c:limit=400&c:show=facility_id,facility_name,zone_id,facility_type_id'
    print(f"url: {url}")
    response = requests.get(url)
    j_data = json.loads(response.content)

    if j_data["returned"] == 0:
        print("Error")
        return

    ids = cfg.base_to_id.values()

    all_bases = list()

    for mp in j_data["map_region_list"]:
        try:
            new_data = dict()
            new_data["_id"] = int(mp["facility_id"])
            new_data["name"] = mp["facility_name"]
            if new_data["_id"] in ids:
                print(f"Adding to pool {new_data['name']}")
                new_data["in_base_pool"] = True
            else:
                new_data["in_base_pool"] = False
            new_data["zone_id"] = int(mp["zone_id"])
            new_data["type_id"] = int(mp["facility_type_id"])
            all_bases.append(new_data)
            if not Base.get(new_data["_id"]):
                print(f"New base found: {new_data['name']}")
        except KeyError:
            print(f"Key error: {mp}")
    db.force_update("static_bases", all_bases)


def players_db_update():
    db.get_all_elements(DbPlayer.new_from_data, "users")
    for p in Player._all_players.values():
        db.set_element("users", p.id, p.get_data())

def get_match_from_db(m_id):
    loop = asyncio.get_event_loop()
    m = loop.run_until_complete(Match.get_from_database(m_id))

    loop.run_until_complete(census.process_score(m))
    _make_image(m)
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(process_score(m))
    # dta=m.get_data()
    # print(f'Match {dta["_id"]}: team1: {dta["teams"][0]["score"]}, team2: {dta["teams"][1]["score"]}')
    # #return dta

    #_make_image(m)

def fill_player_stats():
    all = dict()
    db.get_all_elements(DbMatch.new_from_data, "matches")
    for m in _all_db_matches:
        for tm in m.data["teams"]:
            for p in tm["players"]:
                if p["discord_id"] not in all:
                    all[p["discord_id"]] = PlayerStat(p["discord_id"])
                all[p["discord_id"]].add_data(m.id, p)
    la = list()
    for x in all.values():
        print(f"add {x.id}")
        la.append(x.get_data())
    db.force_update("player_stats", la)

def remove_old_accounts():
    db.get_all_elements(DbPlayer.new_from_data, "users")
    ids = range(1185, 1186)
    for pid in ids:
        print(str(pid))
        p = Player.get(pid)
        db.remove_element("users", p.id)


def matches_time_stat():
    db.get_all_elements(DbMatch.new_from_data, "matches")
    for m in _all_db_matches:
        m.get_played_time()
    d = dict()
    for p in _match_played_dict.keys():
        d[p] = (min(_match_played_dict[p]), max(_match_played_dict[p]))
    return d



# k=matches_time_stat()
# for p in k.keys():
#     print(f"{p}: min:{(k[p][0]-14)%24}, max:{(k[p][1]-14)%24}")

#matches_db_update()
def init_restart_data():
    d= dict()
    d["_id"] = 0
    d["last_match_id"] = 1973
    db.set_element("restart_data", 0, d)



#get_match_from_db(1103)
# ij = 817
# while True:
#     dta=get_match_from_db(ij)
#     if dta:
#         collections["matches"].replace_one({"_id": dta["_id"]}, dta)
#     ij-=1
push_accounts_to_users()