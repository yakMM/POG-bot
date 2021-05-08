from gspread import service_account
from numpy import array
import modules.config as cfg
from classes import Player, Base
import requests
import json
import asyncio
import os

import modules.database as db
import modules.accounts_handler as accounts
from classes import PlayerStat

if os.path.isfile("test"):
    LAUNCHSTR = "_test"
else:
    LAUNCHSTR = ""
cfg.get_config(LAUNCHSTR)
db.init(cfg.database)


def get_accounts():
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
    accs = get_accounts()
    for acc in accs:
        dta = dict()
        dta["_id"] = int(acc)
        dta["usages"] = list()
        dta["unique_usages"] = list()
        db.set_element("accounts_usage", int(acc), dta)


def push_accounts_to_users():
    accs = get_accounts()
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


_all_db_matches = list()


class DbMatch:
    @classmethod
    def new_from_data(cls, data):
        obj = cls(data)
        _all_db_matches.append(obj)

    def __init__(self, data):
        self.data = data
        self.id = data["_id"]


def fill_player_stats():
    all_players = dict()
    db.get_all_elements(DbMatch.new_from_data, "matches")
    for m in _all_db_matches:
        for tm in m.data["teams"]:
            for p in tm["players"]:
                if p["discord_id"] not in all_players:
                    all_players[p["discord_id"]] = PlayerStat(p["discord_id"], "N/A")
                all_players[p["discord_id"]].add_data(m.id, m.data["round_length"] * 2, p)
    la = list()
    for x in all_players.values():
        print(f"add {x.id}")
        la.append(x.get_data())
    db.force_update("player_stats", la)

fill_player_stats()