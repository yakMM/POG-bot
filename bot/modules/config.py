""" Retreives configuration from the config file
"""

from json import loads
from requests import get
from configparser import ConfigParser, ParsingError
from modules.exceptions import ConfigError

## STATIC PARAMETERS:
AFK_TIME = 15  # minutes
ROUND_LENGHT = 10  # minutes

## DYNAMIC PARAMETERS:
# (pulled from the config file)

channels = {
    "lobby": 0,
    "register": 0,
    "matches": list(),
    "results": 0,
    "rules": 0,
    "staff": 0,
    "muted": 0
}

channelsList = list()

roles = {
    "admin": 0,
    "info": 0,
    "registered": 0,
    "notify": 0
}

# General

general = {
    "token": "",
    "api_key": "",
    "command_prefix": "",
    "lobby_size": 0,
    "rules_msg_id": 0
}

scores = {
    "teamkill" : 0,
    "suicide" : 0,
    "capture" : 0,
    "recapture" : 0
}

VERSION = "0"

factions = {
    1: "VS",
    2: "NC",
    3: "TR"
}

# Lazy way to get factions from user input:
i_factions = {
    "VS": 1,
    "NC": 2,
    "TR": 3
}

# http://census.daybreakgames.com/get/ps2:v2/zone?c:limit=100
zones = {
    2: "Indar",
    4: "Hossin",
    6: "Amerish",
    8: "Esamir"
}

# http://census.daybreakgames.com/get/ps2:v2/facility_type?c:limit=100
facilitiy_suffix = {
    2: "Amp Station",
    3: "Bio Lab",
    4: "Tech Plant"
}


# Database

_collections = {
    "users": "",
    "sBases": "",
    "sWeapons" : ""
}

database = {
    "url": "",
    "cluster": "",
    "accounts": "",
    "collections": _collections
}

# Methods


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
            if isinstance(general[key], int):
                general[key] = int(config['General'][key])
            else:
                general[key] = config['General'][key]
        except KeyError:
            _errorMissing(key, 'General', file)
        except ValueError:
            _errorIncorrect(key, 'General', file)

    # Testing api key
    url = f"http://census.daybreakgames.com/s:{general['api_key']}/get/ps2:v2/faction"
    jdata = loads(get(url).content)
    if 'error' in jdata:
        raise ConfigError(
            f"Incorrect api key: {general['api_key']} in '{file}'")

    # Channels section
    _checkSection(config, "Channels", file)

    for key in channels:
        try:
            if key == "matches":
                tmp = config['Channels'][key].split(',')
                channels[key].clear()
                for m in tmp:
                    channels[key].append(int(m))
                    channelsList.append(int(m))
            else:
                channels[key] = int(config['Channels'][key])
                channelsList.append(channels[key])
        except KeyError:
            _errorMissing(key, 'Channels', file)
        except ValueError:
            _errorIncorrect(key, 'Channels', file)

    # Roles section
    _checkSection(config, "Roles", file)
    for key in roles:
        try:
            roles[key] = int(config['Roles'][key])
        except KeyError:
            _errorMissing(key, 'Roles', file)
        except ValueError:
            _errorIncorrect(key, 'Roles', file)
    
    # Scores section
    _checkSection(config, "Scores", file)
    for key in scores:
        try:
            scores[key] = int(config['Scores'][key])
        except KeyError:
            _errorMissing(key, 'Scores', file)
        except ValueError:
            _errorIncorrect(key, 'Scores', file)

    # Database section
    _checkSection(config, "Database", file)

    for key in database:
        if key != "collections":
            try:
                database[key] = config['Database'][key]
            except KeyError:
                _errorMissing(key, 'Database', file)

    # Collections section
    _checkSection(config, "Collections", file)

    for key in database["collections"]:
        try:
            database["collections"][key] = config['Collections'][key]
        except KeyError:
            _errorMissing(key, 'Collections', file)

    # Version
    with open('../CHANGELOG.md', 'r', encoding='utf-8') as txt:
        txt_str = txt.readline()
    global VERSION
    # Extracts "X.X.X" from string "# vX.X.X:" in a lazy way
    VERSION = txt_str[3:-2]


def _checkSection(config, section, file):
    if not section in config:
        raise ConfigError(f"Missing section '{section}' in '{file}'")


def _errorMissing(field, section, file):
    raise ConfigError(f"Missing field '{field}' in '{section}' in '{file}'")


def _errorIncorrect(field, section, file):
    raise ConfigError(f"Incorrect field '{field}' in '{section}' in '{file}'")
