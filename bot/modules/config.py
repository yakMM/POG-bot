""" Retreives configuration from the config file
"""

from json import loads
from requests import get
from configparser import ConfigParser, ParsingError
from modules.exceptions import ConfigError

## DiscordIds

discord_ids = {
    "lobby" : 0,
    "register" : 0,
    "matches" : list(),
    "results" : 0,
    "rules" : 0,
    "rules_msg" : 0,
    "admin_role" : 0,
    "info_role" : 0,
    "registered_role" : 0,
    "notify_role" : 0
    }

## General

general = {
    "token" : "",
    "api_key" : "",
    "command_prefix" : "",
    "lobby_size" : 0
    }

AFK_TIME = 15 # minutes

factions = {
    1 : "VS",
    2 : "NC",
    3 : "TR"
}

# Lazy way to get factions from user input:
i_factions = {
    "VS" : 1,
    "NC" : 2,
    "TR" : 3
}

# http://census.daybreakgames.com/get/ps2:v2/zone?c:limit=100
zones = {
2 : "Indar",
4 : "Hossin",
6 : "Amerish",
8 : "Esamir"
}

# http://census.daybreakgames.com/get/ps2:v2/facility_type?c:limit=100
facilitiy_suffix = {
2 : "Amp Station",
3 : "Bio Lab",
4 : "Tech Plant"
}

PIL_MAPS_IDS = [3430,302030,239000,305010,230,307010] #peris, can, pale, ghanan, xeno, chac


## Database

_collections = {
    "users" : "",
    "sBases" : ""
    }

database = {
    "url" : "",
    "cluster" : "",
    "accounts" : "",
    "collections" : _collections
    }

## Methods

def getConfig(file):
    config = ConfigParser()
    try:
        config.read(file)
    except ParsingError as e:
        raise ConfigError(f"Parsing Error in '{file}'")


    # General section
    _checkSection(config, "General", file)

    for key in general:
        try:
            if isinstance(general[key],int):
                general[key]=int(config['General'][key])
            else:
                general[key]=config['General'][key]
        except KeyError:
            _errorMissing(key, 'General', file)
        except ValueError:
            _errorIncorrect(key, 'General', file)

    # Testing api key
    url = f"http://census.daybreakgames.com/s:{general['api_key']}/get/ps2:v2/faction"
    jdata=loads(get(url).content)
    if 'error' in jdata:
        raise ConfigError(f"Incorrect api key: {general['api_key']} in '{file}'")


    # Discord_Ids section
    _checkSection(config, "Discord_Ids", file)

    for key in discord_ids:
        try:
            if key == "matches":
                tmp = config['Discord_Ids'][key].split(',')
                discord_ids[key].clear()
                for m in tmp:
                    discord_ids[key].append(int(m))
            else:
                discord_ids[key] = int(config['Discord_Ids'][key])
        except KeyError:
            _errorMissing(key, 'Discord_Ids', file)
        except ValueError:
            _errorIncorrect(key, 'Discord_Ids', file)


    # Database section
    _checkSection(config, "Database", file)

    for key in database:
        if key != "collections":
            try:
                database[key]=config['Database'][key]
            except KeyError:
                _errorMissing(key, 'Database', file)


    # Collections section
    _checkSection(config, "Collections", file)


    for key in database["collections"]:
        try:
            database["collections"][key] = config['Collections'][key]
        except KeyError:
            _errorMissing(key, 'Collections', file)


def _checkSection(config, section, file):
    if not section in config:
        raise ConfigError(f"Missing section '{section}' in '{file}'")

def _errorMissing(field, section, file):
    raise ConfigError(f"Missing field '{field}' in '{section}' in '{file}'")


def _errorIncorrect(field, section, file):
    raise ConfigError(f"Incorrect field '{field}' in '{section}' in '{file}'")