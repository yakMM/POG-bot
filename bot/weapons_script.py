"""
| Script for populating the weapon database.
| Tools for interacting with weapons listed in the census API
"""

# External imports
import requests
import json
import os

# Internal imports
import modules.config as cfg
from modules.database import force_update, init as db_init, get_all_elements
import classes
import pathlib

# Find if we are in test mode or in production
if os.path.isfile(f"{pathlib.Path(__file__).parent.absolute()}/test"):
    LAUNCHSTR = "_test"
else:
    LAUNCHSTR = ""

# Init config file and database, get all weapons currently in db
cfg.get_config(LAUNCHSTR)
db_init(cfg.database)
get_all_elements(classes.Weapon, "static_weapons")

item_type_id = 26  # weapon

# List of all categories
we_cats = {
    2: 'Knife',  # DET
    3: 'Pistol',  # DET
    8: 'Carbine',  # DET
    7: 'Assault Rifle',  # DET
    139: 'Infantry Abilities',  # BAN
    4: 'Shotgun',  # BAN
    6: 'LMG',  # DET
    13: 'Rocket Launcher',  # NP, DET
    11: 'Sniper Rifle',  # DET
    18: 'Explosive',  # BAN
    17: 'Grenade',  # DET
    5: 'SMG',  # DET
    19: 'Battle Rifle',  # DET
    24: 'Crossbow',  # ALL
    12: 'Scout Rifle',  # ALL
    10: 'AI MAX (Left)',  # BAN
    14: 'Heavy Weapon',  # BAN
    21: 'AV MAX (Right)',  # BAN
    20: 'AA MAX (Right)',  # BAN
    22: 'AI MAX (Right)',  # BAN
    9: 'AV MAX (Left)',  # BAN
    23: 'AA MAX (Left)',  # BAN
    147: 'Aerial Combat Weapon',  # ALL
    104: 'Vehicle Weapons',  # BAN
    211: 'Colossus Primary Weapon',  # BAN
    144: 'ANT Top Turret',  # BAN
    157: 'Hybrid Rifle',  # BAN
    126: 'Reaver Wing Mount',  # BAN
    208: 'Bastion Point Defense',  # BAN
    209: 'Bastion Bombard',  # BAN
    210: 'Bastion Weapon System'  # BAN
}

# Discrimination per category
ignored_categories = []  # [104,211,144,157,126,208,209,210,139] Switched this to banned
banned_categories = [21, 20, 22, 9, 23, 10, 18, 14, 4, 104, 211, 144, 157, 126, 208, 209, 210, 139]
allowed_categories = [24, 12]
detailed = [2, 3, 5, 6, 7, 8, 11, 17, 19, 13]
no_point = [13, 17, 147]


def get_banned_per_category(cat: int, w_id: int) -> bool:
    """
    Determine if a weapon is banned.

    :param cat: Category of the weapon.
    :param w_id: Id of the weapon.
    :return: True if the weapon is banned, False if not.
    """
    d = dict()
    # Edit this function to change the ruleset:
    # To ban a weapon, add it to the dict, to unban it remove it.

    # Knife
    if cat == 2:
        d = {
            271: "Carver",
            285: "Ripper",
            286: "Lumine Edge",
            1082: "MAX Punch",
            1083: "MAX Punch",
            1084: "MAX Punch",
            6005451: "Lumine Edge AE",
            6005452: "Ripper AE",
            6005453: "Carver AE",
            6008687: "Defector Claws",
            600946: "NS Icebreaker",
            6009515: "NS Icebreaker",
            6009516: "NS Icebreaker",
            6009517: "NS Icebreaker",
            6009518: "NS Icebreaker",
            6009600: "NS Firebug"
        }
    # Pistol
    elif cat == 3:
        d = {
            1889: "The Executive",
            1954: "The President",
            1959: "The Immortal",
            7390: "NC08 Mag-Scatter",
            802733: "NS-44L Blackhand",
            802781: "NS-44LB Blackhand",
            802782: "NS-44LG Blackhand",
            804960: "NS-44LP Blackhand",
            6002661: 'NS-44L "Ravenous" Blackhand',
            6003793: "NS-44L Showdown",
            6003943: "NS-357 IA",
            6004714: "Soldier Soaker",
            6004995: "Ectoblaster",
            6005969: "NSX-A Yawara",
            6009652: 'NS-357 "Endeavor" Underboss',
            6009902: "U-100 Lastly",
            6009903: "U-150 Recall",
            6009904: "U-200 Harbinger"
        }
    # SMG
    elif cat == 5:
        d = {
            1899: "Tempest",
            1944: "Shuriken",
            1949: "Skorpios",
            27000: "AF-4 Cyclone",
            27005: "AF-4G Cyclone",
            28000: "SMG-46 Armistice",
            28005: "SMG-46G Armistice",
            29000: "Eridani SX5",
            29005: "Eridani SX5G",
            6002772: "Eridani SX5-AE",
            6002800: "SMG-46AE Armistice",
            6002824: "AF-4AE Cyclone",
            6003850: "MGR-S1 Gladius",
            6003879: "MG-S1 Jackal",
            6003925: "VE-S Canis",
            6005968: "NSX-A Kappa",
            6009203: "NS-66 Punisher"
        }
    # LMG
    elif cat == 6:
        d = {
            1879: "NC6A GODSAW",
            1894: "Betelgeuse 54-A",
            1924: 'T9A "Butcher"'
        }
    # Assault Rifle
    elif cat == 7:
        d = {
            1904: "T1A Unity",
            1909: "Darkstar",
            77822: "Gauss Prime",
            6009864: "AR-100",
            6009891: "AR-101",
            6009892: "AR-N203",
            6009893: "CB-100",
            6009894: "CB-X75",
            6009895: "CB-200",
            6009896: "PMG-100",
            6009897: "PMG-200",
            6009898: "PMG-3XB",
            6009899: "XMG-100",
            6009900: "XMG-155",
            6009901: "XMG-200"
        }
    # Carbine
    elif cat == 8:
        d = {
            1869: "19A Fortuna",
            1914: "TRAC-Shot",
            1919: "Eclipse VE3A"
        }
    elif cat == 13:
        d = {
            1964: "The Kraken"
        }
    # Sniper Rifle
    elif cat == 11:
        d = {
            1969: "The Moonshot",
            1974: "Bighorn .50M",
            1979: "Parsec VX3-A"
        }
    # Grenades
    elif cat == 17:
        d = {
            6050: "Decoy Grenade",
            6003418: "NSX Fujin",
            6004742: "Water Balloon",
            6004743: "Water Balloon",
            6004744: "Water Balloon",
            6004750: "Flamewake Grenade",
            6005304: "Smoke Grenade",
            6005472: "NSX Raijin",
            6007252: "Water Balloon",
            6009459: "Lightning Grenade",
            6009524: "Condensate Grenade",
            6009583: "Infernal Grenade"
        }
    # Battle Rifle
    elif cat == 19:
        d = {
            1984: "GD Guardian",
            1989: "DMR-99",
            1994: "Revenant",
            6004209: "MGR-M1 Bishop",
            6004214: "VE-LR Obelisk",
            6004216: "MG-HBR1 Dragoon",
            6005970: "NSX-A Sesshin",
            6009101: "NS-30 Tranquility"
        }
    return w_id in d.keys()


def get_unknown_weapon():
    n_data = dict()
    n_data["_id"] = 0
    n_data["name"] = "Unknown"
    n_data["points"] = 1
    n_data["banned"] = False
    n_data["faction"] = 0
    n_data["cat_id"] = 0
    return n_data


def push_all_weapons(push_db=False):
    giga_list = list()
    for cat in we_cats.keys():

        # If category to ignore
        if cat in ignored_categories:
            continue

        # Else get all weapons from the category
        url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/item/' \
              f'?item_type_id=26&is_vehicle_weapon=0&item_category_id={cat}' \
              f'&c:limit=5000&c:show=item_id,item_category_id,name.en,faction_id'
        response = requests.get(url)
        j_data = json.loads(response.content)
        print(we_cats[cat])  # Print category name

        print(url)
        if "returned" not in j_data:
            raise ValueError("Nothing returned!")
        if j_data["returned"] == 0:
            raise ValueError("Nothing returned!")

        # Iterate trough weapons of this category
        for we in j_data["item_list"]:
            n_data = dict()
            n_data["_id"] = int(we["item_id"])  # Weapon ID
            if n_data["_id"] == 0:
                raise ValueError("ID = 0")
            try:
                n_data["name"] = we["name"]["en"]  # Weapon name
            except KeyError:
                n_data["name"] = "Unknown"
                print("Unknown weapon, id: " + we["item_id"])
            try:
                n_data["faction"] = int(we["faction_id"])  # Get weapon's faction
            except KeyError:
                n_data["faction"] = 0
            n_data["cat_id"] = int(we["item_category_id"])  # Weapon category

            # If whole category is banned, weapon is banned
            if cat in banned_categories:
                n_data["points"] = 0
                n_data["banned"] = True
            elif cat in detailed:
                # Else find if weapon is banned
                if get_banned_per_category(cat, n_data["_id"]):
                    # Banned
                    n_data["points"] = 0
                    n_data["banned"] = True
                else:
                    # Not banned, check if weapon should give points
                    if cat in no_point:
                        n_data["points"] = 0
                    else:
                        n_data["points"] = 1
                    n_data["banned"] = False

            # If whole category is allowed
            elif cat in allowed_categories:
                n_data["points"] = 1
                n_data["banned"] = False

            # If whole category gives no point
            elif cat in no_point:
                n_data["points"] = 0
                n_data["banned"] = False

            giga_list.append(n_data)

            # Find weapons new to database:
            if not classes.Weapon.get(n_data["_id"]):
                print(f'Weapon not found in database: '
                      f'cat : {n_data["cat_id"]}, name: {n_data["name"]}, id: {n_data["_id"]}')

    # Add the unknown weapon to the list
    giga_list.append(get_unknown_weapon())
    if push_db:
        # Update db
        force_update("static_weapons", giga_list)
        print("DB updated!")
    else:
        print("DB not updated! Use arg 'push_db=True' to update")


def display_weapons_from_category(cat):
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/item/' \
          f'?item_type_id=26&is_vehicle_weapon=0&item_category_id={cat}' \
          f'&c:limit=5000&c:show=item_id,item_category_id,name.en,faction_id'
    response = requests.get(url)
    j_data = json.loads(response.content)
    if j_data["returned"] == 0:
        print("Error")
        return
    for we in j_data["item_list"]:
        print(f"{we['item_id']};{we['name']['en']}")


def get_all_categories():
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/item_category/?c:limit=500'
    response = requests.get(url)
    j_data = json.loads(response.content)

    if j_data["returned"] == 0:
        print("Error")
        return

    di = dict()
    for cat in j_data["item_category_list"]:
        di[int(cat["item_category_id"])] = cat["name"]["en"]
    return di


def get_weapons_categories():
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/item/' \
          f'?item_type_id=26&is_vehicle_weapon=0&c:limit=5000' \
          f'&c:show=item_id,item_category_id,name.en'
    response = requests.get(url)
    j_data = json.loads(response.content)
    if j_data["returned"] == 0:
        print("Error")
        return
    cats = list()

    for we in j_data["item_list"]:
        we["_id"] = int(we.pop("item_id"))
        try:
            we["name"] = we.pop("name")["en"]
        except KeyError:
            print(f'KeyError on name of id {we["_id"]}')
        try:
            we["cat_id"] = int(we.pop("item_category_id"))
            if we["cat_id"] not in cats:
                cats.append(we["cat_id"])
        except KeyError:
            print(f'KeyError on cat of id {we["_id"]}')

    return cats
