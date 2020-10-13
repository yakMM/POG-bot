# @CHECK 2.0 features OK

from gspread import service_account
from numpy import array
import modules.config as cfg
from classes.players import Player, _allPlayers, getPlayer
from modules.database import forceUpdate, getAllItems, _replacePlayer, _updateMap, init as dbInit, getOneItem, collections, _remove
from classes.maps import _allMapsList, Map
from matches import Match
import requests
import json
import asyncio
from modules.imageMaker import _makeImage
from classes.weapons import Weapon

LAUNCHSTR = "_test"  # this should be empty if your files are config.cfg and gspread_client_secret.json

cfg.getConfig(f"config{LAUNCHSTR}.cfg")
dbInit(cfg.database)
getAllItems(Player.newFromData, "users")
getAllItems(Map, "sBases")
getAllItems(Weapon, "sWeapons")


class DbPlayer(Player):
    @classmethod
    def newFromData(cls, data):
        newData = dict()
        newData["name"] = data["name"]
        newData["_id"] = data["_id"]
        newData["rank"] = data["rank"]
        newData["notify"] = data["notify"]
        newData["timeout"] = data["timeout"]
        newData["igIds"] = [int(pId) for pId in data["igIds"]]
        newData["igNames"] = list()
        for ig in data["igNames"]:
            bl = ord('0') <= ord(ig[-1]) <= ord('9')
            bl = bl and ord('0') <= ord(ig[-2]) <= ord('9')
            bl = bl and ig[-3] == 'x'
            if bl: # is PIL char?
                print(ig)
                ig = f"pil_{ig}"
            newData["igNames"].append(ig)

        newData["hasOwnAccount"] = data["hasOwnAccount"]
        super().newFromData(newData)

_allDbMatches = list()
convert_dict_1 = dict()
convert_dict_2 = dict()

class DbMatch:
    @classmethod
    def newFromData(cls, data):
        obj = cls(data)
        _allDbMatches.append(obj)

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




def pushAccounts():
    # Get all accounts
    gc = service_account(filename=f'google_api_secret{LAUNCHSTR}.json')
    sh = gc.open_by_key(cfg.database["accounts"])
    rawSheet = sh.get_worksheet(1)
    visibleSheet = sh.get_worksheet(0)
    sheetTab = array(rawSheet.get_all_values())

    numAccounts = sheetTab.shape[1] - 3

    accounts = list()
    pList = list()

    # Get all accounts
    for i in range(numAccounts):
        accounts.append(sheetTab[0][i + 3])
    loop = asyncio.get_event_loop()

    for acc in accounts:
        p = Player(int(acc), f"_POG_ACC_{acc}")
        pList.append(p)
        print(acc)
        charList = [f"POGx{acc}VS", f"POGx{acc}TR", f"POGx{acc}NC"]
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


def playersDbUpdate():
    getAllItems(DbPlayer.newFromData, "users")
    for p in _allPlayers.values():
        _replacePlayer(p)

def getMatchFromDb(mId):
    m=getOneItem("matches", Match.newFromData, mId)
    _makeImage(m)

def matchesDbUpdate():
    getAllItems(DbMatch.newFromData, "matches")
    for m in _allDbMatches:
        m.do_change()
    for m in _allDbMatches:
        collections["matches"].replace_one({"_id": m.id}, m.data)

def removeOldAccounts():
    getAllItems(DbPlayer.newFromData, "users")
    ids = range(891, 915)
    for pid in ids:
        print(str(pid))
        p = getPlayer(pid)
        _remove(p)


playersDbUpdate()
