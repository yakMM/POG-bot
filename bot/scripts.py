# @CHECK 2.0 features OK

from gspread import service_account
from numpy import array
import modules.config as cfg
from classes.players import Player, _all_players, get_player
from modules.database import force_update, get_all_items, _replace_player, _update_map, init as db_init, get_one_item, collections, _remove
from classes.maps import _all_maps_list, Map
from matches import Match
import requests
import json
import asyncio
from modules.image_maker import _make_image
from classes.weapons import Weapon

LAUNCHSTR = "_test"  # this should be empty if your files are config.cfg and gspread_client_secret.json

cfg.get_config(f"config{LAUNCHSTR}.cfg")
db_init(cfg.database)
#get_all_items(Player.new_from_data, "users")
get_all_items(Map, "s_bases")
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
        new_data["ig_ids"] = [int(p_id) for p_id in data["ig_ids"]]
        new_data["ig_names"] = [p_name for p_name in data["ig_names"]]
        # new_data["ig_names"] = list()
        # for ig in data["ig_names"]:
        #     bl = ord('0') <= ord(ig[-1]) <= ord('9')
        #     bl = bl and ord('0') <= ord(ig[-2]) <= ord('9')
        #     bl = bl and ig[-3] == 'x'
        #     if bl: # is PIL char?
        #         print(ig)
        #         ig = f"flip_{ig}"
        #     new_data["ig_names"].append(ig)

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


def get_all_maps_from_api():
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2/map_region/?c:limit=400&c:show=facility_id,facility_name,zone_id,facility_type_id'
    response = requests.get(url)
    jdata = json.loads(response.content)

    if jdata["returned"] == 0:
        print("Error")
        return

    ids = [302030, 239000, 305010, 230, 3430, 3620, 307010]
    # acan,pale,ghanan,xenotech,peris,rashnu,chac

    for mp in jdata["map_region_list"]:
        mp["_id"] = int(mp.pop("facility_id"))
        mp["in_map_pool"] = mp["_id"] in ids
        mp["zone_id"] = int(mp.pop("zone_id"))
        mp["type_id"] = int(mp.pop("facility_type_id"))
    force_update("s_bases", jdata["map_region_list"])


def players_db_update():
    get_all_items(DbPlayer.new_from_data, "users")
    for p in _all_players.values():
        _replace_player(p)

def get_match_from_db(m_id):
    m=get_one_item("matches", Match.new_from_data, m_id)
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


players_db_update()
