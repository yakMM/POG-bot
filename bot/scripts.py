from gspread import service_account
from numpy import array
import modules.config as cfg
from classes.players import Player, _allPlayers
from modules.database import forceUpdate, getAllItems, _replacePlayer, _updateMap, init as dbInit, getOneItem
from classes.maps import _allMapsList, Map
from matches import Match
import requests
import json
import asyncio
from modules.imageMaker import _makeImage
from classes.weapons import Weapon

LAUNCHSTR = ""  # this should be empty if your files are config.cfg and gspread_client_secret.json

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
        newData["igNames"] = data["igNames"]
        newData["hasOwnAccount"] = data["hasOwnAccount"]
        super().newFromData(newData)


def pushAccounts():
    # Get all accounts
    gc = service_account(filename=f'gspread_client_secret{LAUNCHSTR}.json')
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


def playersDbUpdate():
    getAllItems(DbPlayer.newFromData, "users")
    for p in _allPlayers.values():
        _replacePlayer(p)

def getMatchFromDb(mId):
    m=getOneItem("matches", Match.newFromData, mId)
    _makeImage(m)



def addPlayer():
    i=900
    pList = [Player(901,"jeanlebonjambeauneau"), Player(902,"jeandlkdfjhlskdhflskdhflsdkhflsdkhf")]
    pList[0].cheatName("JEANxebonjambeauneTR")
    pList[1].cheatName("lsdfkjqlfmkhsdfmlkshmgflskhdngmlskdhg")
    for p in pList:
        _replacePlayer(p)
