from gspread import service_account
from numpy import array
import modules.config as cfg
from modules.database import _update, init as dbInit
from classes.players import Player
from modules.database import forceBasesUpdate
import requests
import json
import asyncio

LAUNCHSTR = "_test" # this should be empty if your files are config.cfg and client_secret.json

cfg.getConfig(f"config{LAUNCHSTR}.cfg")
dbInit(cfg.database)

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
        charList=[f"PSBx{acc}VS", f"PSBx{acc}TR", f"PSBx{acc}NC"]
        p._hasOwnAccount = True
        loop.run_until_complete(p._addCharacters(charList))
        _update(p)
    loop.close()



def getAllMapsFromApi():


    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2/map_region/?c:limit=400&c:show=facility_id,facility_name,zone_id,facility_type_id'
    response = requests.get(url)
    jdata=json.loads(response.content)

    if jdata["returned"] == 0:
        print("Error")
        return

    for mp in jdata["map_region_list"]:
        mp["_id"] = int(mp.pop("facility_id"))
        mp["zone_id"] = int(mp.pop("zone_id"))
        mp["type_id"] = int(mp.pop("facility_type_id"))
    forceBasesUpdate(jdata["map_region_list"])