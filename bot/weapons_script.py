# @CHECK 2.0 features OK

import modules.config as cfg
from modules.database import force_update, init as db_init, get_all_items
import requests
import json
import os
from classes.weapons import Weapon, get_weapon
from general.exceptions import ElementNotFound

if os.path.isfile("test"):
    LAUNCHSTR = "_test"
else:
    LAUNCHSTR = ""

cfg.get_config(f"config{LAUNCHSTR}.cfg")
db_init(cfg.database)
get_all_items(Weapon, "s_weapons")

item_type_id = 26 #weapon

we_cats = {
    2:  'Knife',                    # DET
    3:  'Pistol',                   # DET
    8:  'Carbine',                  # ALL
    7:  'Assault Rifle',            # ALL
    139:'Infantry Abilities',       # REMOVE
    4:  'Shotgun',                  # BAN
    6:  'LMG',                      # ALL
    13: 'Rocket Launcher',          # NP
    11: 'Sniper Rifle',             # DET
    18: 'Explosive',                # BAN
    17: 'Grenade',                  # NP
    5:  'SMG',                      # DET
    19: 'Battle Rifle',             # BAN
    24: 'Crossbow',                 # ALL
    12: 'Scout Rifle',              # DET
    10: 'AI MAX (Left)',            # BAN
    14: 'Heavy Weapon',             # BAN
    21: 'AV MAX (Right)',           # BAN
    20: 'AA MAX (Right)',           # BAN
    22: 'AI MAX (Right)',           # BAN
    9:  'AV MAX (Left)',            # BAN
    23: 'AA MAX (Left)',            # BAN
    147:'Aerial Combat Weapon',     # BAN
    104:'Vehicle Weapons',          # REMOVE
    211:'Colossus Primary Weapon',  # REMOVE
    144:'ANT Top Turret',           # REMOVE
    157:'Hybrid Rifle',             # REMOVE
    126:'Reaver Wing Mount',        # REMOVE
    208:'Bastion Point Defense',    # REMOVE
    209:'Bastion Bombard',          # REMOVE
    210:'Bastion Weapon System'     # REMOVE
}


ignored_categories = [] # [104,211,144,157,126,208,209,210,139] Switched this to banned
banned_categories  = [21,20,22,9,23,10,18,147,14,4,104,211,144,157,126,208,209,210,139]
allowed_categories = [24,12]
detailled = [2,3,5,6,7,8,11,17,19]
no_point = [13,17]


def get_banned_per_categorie(cat, id):
    # Knife
    if cat == 2:
        d = {
        271:        "Carver",
        285:        "Ripper",
        286:        "Lumine Edge",
        1082:       "MAX Punch",
        1083:       "MAX Punch",
        1084:       "MAX Punch",
        804795:     "NSX Amaterasu",
        6005451:    "Lumine Edge AE",
        6005452:    "Ripper AE",
        6005453:    "Carver AE",
        6008687:    "Defector Claws",
        600946:     "NS Icebreaker",
        6009515:    "NS Icebreaker",
        6009516:    "NS Icebreaker",
        6009517:    "NS Icebreaker",
        6009518:    "NS Icebreaker",
        6009600:    "NS Firebug"
        }
    # Pistol
    elif cat == 3:
        d={
        1889:       "The Executive",
        1954:       "The President",
        1959:       "The Immortal",
        7390:       "NC08 Mag-Scatter",
        802733:     "NS-44L Blackhand",
        802781:     "NS-44LB Blackhand",
        802782:     "NS-44LG Blackhand",
        804960:     "NS-44LP Blackhand",
        6002661:    'NS-44L "Ravenous" Blackhand',
        6003793:    "NS-44L Showdown",
        6003943:    "NS-357 IA",
        6004714:    "Soldier Soaker",
        6004995:    "Ectoblaster",
        6005969:    "NSX-A Yawara",
        6009652:    'NS-357 "Endeavor" Underboss'
        }
    # SMG
    elif cat == 5:
        d={
        1899:       "Tempest",
        1944:       "Shuriken",
        1949:       "Skorpios",
        27000:      "AF-4 Cyclone",
        27005:      "AF-4G Cyclone",
        28000:      "SMG-46 Armistice",
        28005:      "SMG-46G Armistice",
        29000:      "Eridani SX5",
        29005:      "Eridani SX5G",
        6002772:    "Eridani SX5-AE",
        6002800:    "SMG-46AE Armistice",
        6002824:    "AF-4AE Cyclone",
        6003850:    "MGR-S1 Gladius",
        6003879:    "MG-S1 Jackal",
        6003925:    "VE-S Canis",
        6005968:    "NSX-A Kappa",
        6009203:    "NS-66 Punisher"
        }
    # LMG
    elif cat == 6:
        d={
        1879:   "NC6A GODSAW",
        1894:   "Betelgeuse 54-A",
        1924:   'T9A "Butcher"'
        }
    # Assault Rifle
    elif cat == 7:
        d={
        1904:   "T1A Unity",
        1909:   "Darkstar",
        77822:  "Gauss Prime"
        }
    # Carbine
    elif cat == 8:
        d={
        1869:   "19A Fortuna",
        1914:   "TRAC-Shot",
        1919:   "Eclipse VE3A"
        }
    # Sniper Rifle
    elif cat == 11:
        d={
        1969:       "The Moonshot",
        1974:       "Bighorn .50M",
        1979:       "Parsec VX3-A",
        802771:     "NS-AM7 Archer",
        802910:     "NS-AM7B Archer",
        802921:     "NS-AM7G Archer",
        804255:     "NSX Daimyo",
        6002918:    "NS-AM7 VS/AE Archer",
        6002930:    "NS-AM7 AE/TR Archer",
        6002943:    "NS-AM7 AE/NC Archer",
        6004294:    "AM7-XOXO",
        6004992:    "NS-AM8 Shortbow",
        6006850:    "SR-200",
        6008496:    "PSA-01 Hammerhead AMR",
        6008652:    'NSX "Ivory" Daimyo',
        6008670:    'NSX "Networked" Daimyo'
        }
    # Grenades
    elif cat == 17:
        d={
        6050:       "Decoy Grenade",
        6003418:    "NSX Fujin",
        6004742:    "Water Balloon",
        6004743:    "Water Balloon",
        6004744:    "Water Balloon",
        6004750:    "Flamewake Grenade",
        6005304:    "Smoke Grenade",
        6005472:    "NSX Raijin",
        6007252:    "Water Balloon",
        6009459:    "Lightning Grenade",
        6009524:    "Condensate Grenade",
        6009583:    "Infernal Grenade"
        }
    # Battle Rifle
    elif cat == 19:
        d={
        1984:       "GD Guardian",
        1989:       "DMR-99",
        1994:       "Revenant",
        6004209:    "MGR-M1 Bishop",
        6004214:    "VE-LR Obelisk",
        6004216:    "MG-HBR1 Dragoon",
        6005970:    "NSX-A Sesshin",
        6009101:    "NS-30 Tranquility"
        }
    return id in d.keys()

def get_weapons_categories():
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/item/?item_type_id=26&is_vehicle_weapon=0&c:limit=5000&c:show=item_id,item_category_id,name.en'
    response = requests.get(url)
    jdata = json.loads(response.content)
    if jdata["returned"] == 0:
        print("Error")
        return
    cats = list()

    for we in jdata["item_list"]:
        we["_id"] = int(we.pop("item_id"))
        try:
            we["name"] = we.pop("name")["en"]
        except KeyError:
            print(f'Key on name of id {we["_id"]}')
        try:
            we["cat_id"] = int(we.pop("item_category_id"))
            if we["cat_id"] not in cats:
                cats.append(we["cat_id"])
        except KeyError:
            print(f'Key on cat of id {we["_id"]}')

    return cats

def get_unknown_weapon():
    n_data=dict()
    n_data["_id"] = 0
    n_data["name"] = "Unknown"
    n_data["points"] = 1
    n_data["banned"] = False
    n_data["faction"] = 0
    n_data["cat_id"] = 0
    return n_data


def push_all_weapons(find_new = False):
    giga_list=list()
    for cat in we_cats.keys():
        if cat in ignored_categories:
            continue
        url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/item/?item_type_id=26&is_vehicle_weapon=0&item_category_id={cat}&c:limit=5000&c:show=item_id,item_category_id,name.en,faction_id'
        response = requests.get(url)
        jdata = json.loads(response.content)
        print(we_cats[cat])
        if jdata["returned"] == 0:
            print("Error")
            return
        for we in jdata["item_list"]:
            n_data = dict()
            n_data["_id"] = int(we["item_id"])
            if n_data["_id"] == 0:
                print("RAAAAA")
            try:
                n_data["name"] = we["name"]["en"]
            except KeyError:
                n_data["name"] = "Unknown"
                print("Unknown weapon, id: " + we["item_id"])
            n_data["cat_id"] = int(we["item_category_id"])
            if cat in banned_categories:
                n_data["points"] = 0
                n_data["banned"] = True
            elif cat in detailled:
                if get_banned_per_categorie(cat, n_data["_id"]):
                    n_data["points"] = 0
                    n_data["banned"] = True
                else:
                    if cat in no_point:
                        n_data["points"] = 0
                    else:
                        n_data["points"] = 1
                    n_data["banned"] = False
            elif cat in allowed_categories:
                n_data["points"] = 1
                n_data["banned"] = False
            elif cat in no_point:
                n_data["points"] = 0
                n_data["banned"] = False
            try:
                n_data["faction"] = int(we["faction_id"])
            except KeyError:
                n_data["faction"]  = 0
            giga_list.append(n_data)
            # To find new weapons:
            if find_new:
                try:
                    get_weapon(n_data["_id"])
                except ElementNotFound:
                    print(f'Weapon not found in database: cat : {n_data["cat_id"]}, name: {n_data["name"]}, id: {n_data["_id"]}')
    giga_list.append(get_unknown_weapon())
    if not find_new:
        print("DB updated!")
        force_update("s_weapons", giga_list)
    else:
        print("DB not updated! Use arg find_new=False to update")


def displayWeaponsFromCategorie(cat):
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/item/?item_type_id=26&is_vehicle_weapon=0&item_category_id={cat}&c:limit=5000&c:show=item_id,item_category_id,name.en,faction_id'
    response = requests.get(url)
    jdata = json.loads(response.content)
    if jdata["returned"] == 0:
        print("Error")
        return
    for we in jdata["item_list"]:
        print(f"{we['item_id']};{we['name']['en']}")

def get_all_categories():
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/item_category/?c:limit=500'
    response = requests.get(url)
    jdata = json.loads(response.content)

    if jdata["returned"] == 0:
        print("Error")
        return

    di = dict()
    for cat in jdata["item_category_list"]:
        di[int(cat["item_category_id"])] = cat["name"]["en"]
    return di
