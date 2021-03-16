""" Retrieves configuration from the config file
"""

from json import loads
from requests import get
from configparser import ConfigParser, ParsingError
from general.exceptions import ConfigError
from logging import getLogger

log = getLogger("pog_bot")

## STATIC PARAMETERS:

AFK_TIME = 15  # minutes

factions = {
    1: "VS",
    2: "NC",
    3: "TR"
}

# Lazy way to get factions from user input:
i_factions = {v: k for k, v in factions.items()}

# http://census.daybreakgames.com/get/ps2:v2/zone?c:limit=100
zones = {
    2: "Indar",
    4: "Hossin",
    6: "Amerish",
    8: "Esamir"
}

# http://census.daybreakgames.com/get/ps2:v2/facility_type?c:limit=100
facility_suffix = {
    2: "Amp Station",
    3: "Bio Lab",
    4: "Tech Plant"
}

# http://census.daybreakgames.com/get/ps2/base_region/?c:limit=400&c:show=facility_id,facility_name,zone_id,facility_type_id
base_to_id = {
    "acan" : 302030,
    "ghanan" : 305010,
    "chac" : 307010,
    "pale" : 239000,
    "peris" : 3430,
    "rashnu" : 3620,
    "xeno" : 230,
    "ns_material" : 224,
    "ceres" : 219,
    "kessel" : 266000,
    "nettlemire" : 283000,
    "bridgewater" : 272000,
    "rime" : 244610
}

id_to_base = {v: k for k, v in base_to_id.items()}

## DYNAMIC PARAMETERS:
# (pulled from the config file)

VERSION = "0"

# General
general = {
    "token": "",
    "api_key": "",
    "command_prefix": "",
    "lobby_size": 0,
    'round_length': 0,
    "rules_msg_id": 0
}

# Teamspeak
ts = {
    "url": "",
    "config_help" : "",
    "lobby_id": 0
}

# Channels
channels = {
    "lobby": 0,
    "register": 0,
    "matches": list(),
    "results": 0,
    "rules": 0,
    "staff": 0,
    "muted": 0,
    "spam": 0
}

channels_list = list()

# Roles
roles = {
    "admin": 0,
    "info": 0,
    "registered": 0,
    "notify": 0
}

# Emojis
emojis = {
    "vs": "",
    "tr": "",
    "nc": ""
}

# Scores
scores = {
    "teamkill": 0,
    "suicide": 0,
    "capture": 0,
    "recapture": 0
}

# Collections
_collections = {
    "users": "",
    "s_bases": "",
    "s_weapons" : "",
    "matches" : ""
}

# Database
database = {
    "url": "",
    "cluster": "",
    "accounts": "",
    "jaeger_cal": "",
    "collections": _collections
}

# Map Images
base_images = dict()


## Methods

def get_config(file):
    config = ConfigParser()
    try:
        config.read(file)
    except ParsingError as e:
        raise ConfigError(f"Parsing Error in '{file}'\n{e}")

    # General section
    _check_section(config, "General", file)

    for key in general:
        try:
            if isinstance(general[key], int):
                general[key] = int(config['General'][key])
            else:
                general[key] = config['General'][key]
        except KeyError:
            _error_missing(key, 'General', file)
        except ValueError:
            _error_incorrect(key, 'General', file)

    # Testing api key
    url = f"http://census.daybreakgames.com/s:{general['api_key']}/get/ps2:v2/faction"
    jdata = loads(get(url).content)
    if 'error' in jdata:
        raise ConfigError(
            f"Incorrect api key: {general['api_key']} in '{file}'")

    # Teamspeak section
    _check_section(config, "Teamspeak", file)

    for key in ts:
        try:
            if isinstance(ts[key], int):
                ts[key] = int(config['Teamspeak'][key])
            else:
                ts[key] = config['Teamspeak'][key]
        except KeyError:
            _error_missing(key, 'Teamspeak', file)
        except ValueError:
            _error_incorrect(key, 'Teamspeak', file)


    # Channels section
    _check_section(config, "Channels", file)

    for key in channels:
        try:
            if key == "matches":
                tmp = config['Channels'][key].split(',')
                channels[key].clear()
                for m in tmp:
                    channels[key].append(int(m))
                    channels_list.append(int(m))
            else:
                channels[key] = int(config['Channels'][key])
                channels_list.append(channels[key])
        except KeyError:
            _error_missing(key, 'Channels', file)
        except ValueError:
            _error_incorrect(key, 'Channels', file)

    # Roles section
    _check_section(config, "Roles", file)
    for key in roles:
        try:
            roles[key] = int(config['Roles'][key])
        except KeyError:
            _error_missing(key, 'Roles', file)
        except ValueError:
            _error_incorrect(key, 'Roles', file)

    # Emojis section
    _check_section(config, "Emojis", file)
    for key in emojis:
        try:
            emojis[key] = config['Emojis'][key]
        except KeyError:
            _error_missing(key, 'Emojis', file)

    # Scores section
    _check_section(config, "Scores", file)
    for key in scores:
        try:
            scores[key] = int(config['Scores'][key])
        except KeyError:
            _error_missing(key, 'Scores', file)
        except ValueError:
            _error_incorrect(key, 'Scores', file)

    # Database section
    _check_section(config, "Database", file)

    for key in database:
        if key != "collections":
            try:
                database[key] = config['Database'][key]
            except KeyError:
                _error_missing(key, 'Database', file)

    # Collections section
    _check_section(config, "Collections", file)

    for key in database["collections"]:
        try:
            database["collections"][key] = config['Collections'][key]
        except KeyError:
            _error_missing(key, 'Collections', file)

    # Version
    with open('../CHANGELOG.md', 'r', encoding='utf-8') as txt:
        txt_str = txt.readline()
    global VERSION
    # Extracts "X.X.X" from string "# vX.X.X:" in a lazy way
    VERSION = txt_str[3:-2]

    # Map_Images section
    _check_section(config, "Map_Images", file)

    for key in config['Map_Images'].keys():
        try:
            base_images[base_to_id[key]] = config['Map_Images'][key]
        except KeyError:
            raise ConfigError(f"Missing base '{key}' in 'base_to_id' dictionary in 'config.py'")


def _check_section(config, section, file):
    if section not in config:
        raise ConfigError(f"Missing section '{section}' in '{file}'")


def _error_missing(field, section, file):
    raise ConfigError(f"Missing field '{field}' in '{section}' in '{file}'")


def _error_incorrect(field, section, file):
    raise ConfigError(f"Incorrect field '{field}' in '{section}' in '{file}'")
