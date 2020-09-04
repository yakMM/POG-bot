from gspread import service_account
from numpy import array
import modules.config as cfg
from classes.players import Player, _allPlayers
from modules.database import forceUpdate, getAllPlayers, _replacePlayer, _updateMap, getAllMaps, init as dbInit
from classes.maps import _allMapsList
import requests
import json
import asyncio

LAUNCHSTR = "_test"  # this should be empty if your files are config.cfg and client_secret.json

cfg.getConfig(f"config{LAUNCHSTR}.cfg")
dbInit(cfg.database)


we_cats ={
    2: 'Knife',#
    3: 'Pistol',#
    8: 'Carbine',#
    7: 'Assault Rifle',#
    139: 'Infantry Abilities', #
    4: 'Shotgun',#
    6: 'LMG',#
    13: 'Rocket Launcher',#
    11: 'Sniper Rifle',#
    18: 'Explosive',#
    17: 'Grenade',#
    5: 'SMG',#
    19: 'Battle Rifle',#
    24: 'Crossbow',#
    12: 'Scout Rifle',#
    10: 'AI MAX (Left)',#
    14: 'Heavy Weapon',
    21: 'AV MAX (Right)',#
    20: 'AA MAX (Right)',#
    22: 'AI MAX (Right)',#
    9: 'AV MAX (Left)',#
    23: 'AA MAX (Left)',#
    147: 'Aerial Combat Weapon',#
    104: 'Vehicle Weapons',#
    211: 'Colossus Primary Weapon',#○
    144: 'ANT Top Turret',#
    157: 'Hybrid Rifle',#
    126: 'Reaver Wing Mount',#
    208: 'Bastion Point Defense',#
    209: 'Bastion Bombard',#
    210: 'Bastion Weapon System'#
 }

class DbPlayer(Player):
    @classmethod
    def newFromData(cls, data):
        newData=dict()
        newData["name"] = data["name"]
        newData["_id"] = data["_id"]
        newData["rank"] = 1
        newData["notify"] = data["roles"]["notify"]
        newData["timeout"] = {"time" : 0, "reason" :""}
        newData["igIds"] = data["igIds"]
        newData["igNames"] = data["igNames"]
        newData["hasOwnAccount"] = data["hasOwnAccount"]
        super().newFromData(newData)

def pushAccounts():
    # Get all accounts
    gc = service_account(filename=f'client_secret{LAUNCHSTR}.json')
    sh = gc.open_by_key(cfg.database["accounts"])
    rawSheet = sh.get_worksheet(1)
    visibleSheet = sh.get_worksheet(0)
    sheetTab = array(rawSheet.get_all_values())

    numAccounts = sheetTab.shape[1]-3

    accounts = list()
    pList = list()

    # Get all accounts
    for i in range(numAccounts):
        accounts.append(sheetTab[0][i+3])
    loop = asyncio.get_event_loop()

    for acc in accounts:
        p = Player(f"_POG_ACC_{acc}", int(acc))
        pList.append(p)
        print(acc)
        charList = [f"PSBx{acc}VS", f"PSBx{acc}TR", f"PSBx{acc}NC"]
        p._hasOwnAccount = True
        loop.run_until_complete(p._addCharacters(charList))
        _replacePlayer(p)
    loop.close()


def getAllMapsFromApi():

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
    forceUpdate("sBases", jdata["map_region_list"])


def getAllWeaponsFromApi(cat=0):
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/item/?item_type_id=26&is_vehicle_weapon=0&item_category_id={cat}&c:limit=5000&c:show=item_id,item_category_id,name'
    response = requests.get(url)
    jdata = json.loads(response.content)
    cats = dict()
    if jdata["returned"] == 0:
        print("Error")
        return

    for we in jdata["item_list"]:
        we["_id"] = int(we.pop("item_id"))
        try:
            we["name"] = we.pop("name")["en"]
            print(f'{we["_id"]};{we["name"]}')
        except KeyError:
            print(f'Key on name of id {we["_id"]}')
        try:
            we["cat_id"] = int(we.pop("item_category_id"))
            if we["cat_id"] not in cats:
                cats[we["cat_id"]] = all_cats[we["cat_id"]]
                #print(all_cats[we["cat_id"]])
        except KeyError:
            print(f'Key on cat of id {we["_id"]}')

    #forceUpdate("sWeapons", jdata["item_list"])
    #return jdata["item_list"]
    #return cats

def getAllCategories():
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/item_category/?c:limit=500'
    response = requests.get(url)
    jdata = json.loads(response.content)

    if jdata["returned"] == 0:
        print("Error")
        return

    di = dict()
    for  cat in jdata["item_category_list"]:
        di[int(cat["item_category_id"])] = cat["name"]["en"]
    return di

def playersDbUpdate():
    getAllPlayers(DbPlayer)
    for p in _allPlayers.values():
        _replacePlayer(p)


def mapDbUpdate():
    getAllMaps()
    for m in _allMapsList:
        print(str(m.id))
        _updateMap(m)

item_type_id = 26 #weapon



#caregories:
