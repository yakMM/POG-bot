# @CHECK 2.0 features OK

from gspread import service_account
from numpy import array
import modules.config as cfg
from classes.players import Player, _all_players, get_player
from modules.database import force_update, get_all_items, _replace_player, _update_base, init as db_init, get_one_item, collections, _remove
from classes.bases import _all_bases_list, Base
from match_process import Match
import requests
import json
import asyncio
from modules.image_maker import _make_image
from classes.weapons import Weapon
import os
from modules.census import process_score

if os.path.isfile("test"):
    LAUNCHSTR = "_test"
else:
    LAUNCHSTR = ""

cfg.get_config(f"config{LAUNCHSTR}.cfg")
db_init(cfg.database)
get_all_items(Player.new_from_data, "users")
get_all_items(Base, "s_bases")
get_all_items(Weapon, "s_weapons")

class DbPlayer(Player):
    @classmethod
    def new_from_data(cls, data):
        new_data = dict()
        new_data["name"] = data["name"]
        new_data["_id"] = data["_id"]
        new_data["rank"] = data["rank"]
        new_data["notify"] = data["notify"]
        new_data["timeout"] = data["timeout"]
        new_data["ig_names"] = data["ig_names"]
        new_data["ig_ids"] = list()
        for i in range(3):
            ig = new_data["ig_names"][i]
            bl = ord('0') <= ord(ig[-1]) <= ord('9')
            bl = bl and ord('0') <= ord(ig[-2]) <= ord('9')
            bl = bl and ig[-3] == 'x'
            if bl: # is PIL char?
                print(ig)
                new_data["ig_ids"].append(0)
            else:
                new_data["ig_ids"].append(data["ig_ids"][i])
        new_data["has_own_account"] = data["has_own_account"]
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

    def do_change(self):
        dt = self.data
        for tm in dt["teams"]:
            for p in tm["players"]:
                try:
                    i_id = p["ig_id"]
                except KeyError:
                    i_name = p["ig_name"]
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




def push_accounts():
    # Get all accounts
    gc = service_account(filename=f'google_api_secret{LAUNCHSTR}.json')
    sh = gc.open_by_key(cfg.database["accounts"])
    raw_sheet = sh.get_worksheet(1)
    visible_sheet = sh.get_worksheet(0)
    sheet_tab = array(raw_sheet.get_all_values())

    num_accounts = sheet_tab.shape[1] - 3

    accounts = list()
    p_list = list()

    # Get all accounts
    for i in range(num_accounts):
        accounts.append(sheet_tab[0][i + 3])
    loop = asyncio.get_event_loop()

    for acc in accounts:
        p = Player(int(acc), f"_POG_ACC_{acc}")
        p_list.append(p)
        print(acc)
        char_list = [f"POGx{acc}VS", f"POGx{acc}TR", f"POGx{acc}NC"]
        p._has_own_account = True
        loop.run_until_complete(p._add_characters(char_list))
        _replace_player(p)
    loop.close()


def get_all_bases_from_api():
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2/base_region/?c:limit=400&c:show=facility_id,facility_name,zone_id,facility_type_id'
    response = requests.get(url)
    jdata = json.loads(response.content)

    if jdata["returned"] == 0:
        print("Error")
        return

    ids = cfg.base_to_id.values()

    all_bases = list()

    for mp in jdata["base_region_list"]:
        try:
            new_data = dict()
            new_data["_id"] = int(mp["facility_id"])
            new_data["name"] = mp["facility_name"]
            new_data["in_base_pool"] = new_data["_id"] in ids
            new_data["zone_id"] = int(mp["zone_id"])
            new_data["type_id"] = int(mp["facility_type_id"])
            all_bases.append(new_data)
        except KeyError:
            print(mp)
    force_update("s_bases", all_bases)


def players_db_update():
    get_all_items(DbPlayer.new_from_data, "users")
    for p in _all_players.values():
        _replace_player(p)

def get_match_from_db(m_id):
    if collections["matches"].count_documents({"_id": m_id}) == 0:
        print(f'{m_id} cancelled!')
        return None
    m=get_one_item("matches", Match.new_from_data, m_id)
    # #print(m.get_data())
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(process_score(m))
    # dta=m.get_data()
    # print(f'Match {dta["_id"]}: team1: {dta["teams"][0]["score"]}, team2: {dta["teams"][1]["score"]}')
    # #return dta

    _make_image(m)

def matches_db_update():
    get_all_items(DbMatch.new_from_data, "matches")
    for m in _all_db_matches:
        m.do_change()
    for m in _all_db_matches:
        collections["matches"].replace_one({"_id": m.id}, m.data)

def remove_old_accounts():
    get_all_items(DbPlayer.new_from_data, "users")
    ids = range(891, 915)
    for pid in ids:
        print(str(pid))
        p = get_player(pid)
        _remove(p)


get_match_from_db(1103)
# ij = 817
# while True:
#     dta=get_match_from_db(ij)
#     if dta:
#         collections["matches"].replace_one({"_id": dta["_id"]}, dta)
#     ij-=1
