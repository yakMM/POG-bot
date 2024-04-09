"""
| Contains all the configuration parameters for the application.
| Call :meth:`get_config` to initialize the configuration from the config file.
"""

from json import loads
from requests import get
from configparser import ConfigParser, ParsingError
from logging import getLogger
import os
import pathlib

log = getLogger("pog_bot")


class ConfigError(Exception):
    """
    Raised when an error occur while reading the config file.

    :param msg: Error message.
    """
    def __init__(self, msg: str):
        self.message = "Error in config file: " + msg
        super().__init__(self.message)

## STATIC PARAMETERS:

name_regex = r"^[ -■]{1,32}$"

#: Dictionary to retrieve faction name by id.
factions = {
    1: "VS",
    2: "NC",
    3: "TR"
}

#: Dictionary to retrieve faction id by name.
i_factions = {v: k for k, v in factions.items()}

# http://census.daybreakgames.com/get/ps2:v2/zone?c:limit=100
#: Dictionary to retrieve zone name by id.
zones = {
    2: "Indar",
    4: "Hossin",
    6: "Amerish",
    8: "Esamir"
}

# http://census.daybreakgames.com/get/ps2:v2/facility_type?c:limit=100
#: Dictionary to retrieve facility suffix by id.
facility_suffix = {
    2: "Amp Station",
    3: "Bio Lab",
    4: "Tech Plant"
}

# http://census.daybreakgames.com/get/ps2:v2/loadout/?c:limit=500
#: Dictionary to retrieve loadout name by id.
loadout_id = {
    1: "infiltrator",
    3: "light_assault",
    4: "medic",
    5: "engineer",
    6: "heavy_assault",
    7: "max",
    8: "infiltrator",
    10: "light_assault",
    11: "medic",
    12: "engineer",
    13: "heavy_assault",
    14: "max",
    15: "infiltrator",
    17: "light_assault",
    18: "medic",
    19: "engineer",
    20: "heavy_assault",
    21: "max"
}

# http://census.daybreakgames.com/get/ps2/base_region/?c:limit=400&c:show=facility_id,facility_name,zone_id,facility_type_id
#: Dictionary to retrieve base id from name.
base_to_id = {
    "acan": 302030,
    "ghanan": 305010,
    "chac": 307010,
    "pale": 239000,
    "peris": 3430,
    "rashnu": 3620,
    "xeno": 230,
    "ns_material": 224,
    "ceres": 219,
    "kessel": 266000,
    "nettlemire": 283000,
    "bridgewater": 272000,
    "rime": 244610
}

#: Dictionary to retrieve base name from id.
id_to_base = {v: k for k, v in base_to_id.items()}

## DYNAMIC PARAMETERS:
# (pulled from the config file)

VERSION = "0"

LAUNCH_STR = ""

GAPI_JSON = ""

#: Contains general parameters.
general = {
    "token": "",
    "api_key": "",
    "command_prefix": "",
    "lobby_size": 0,
    'round_length': 0,
    "squittal_url": ""
}

#: Contains TS3 parameters.
ts = {
    "url": "",
    "config_help": "",
    "lobby_id": 0,
    "matches": list()
}

#: Contains discord channel IDs.
channels = {
    "lobby": 0,
    "register": 0,
    "matches": list(),
    "results": 0,
    "rules": 0,
    "staff": 0,
    "muted": 0,
    "spam": 0,
    "usage": 0
}

#: Contains all channels the bot should read/interact in.
channels_list = list()

#: Contains discord roles IDs.
roles = {
    "admin": 0,
    "registered": 0,
    "notify": 0
}

#: Contains discord emojis IDs.
emojis = {
    "VS": ":vs:",
    "TR": ":tr:",
    "NC": ":nc:",
    "info": ":info:"
}

#: Contains scoring parameters.
scores = {
    "teamkill": 0,
    "suicide": 0,
    "capture": 0,
    "recapture": 0
}

# Contains database collections names.
_collections = {
    "users": "",
    "static_bases": "",
    "static_weapons": "",
    "matches": "",
    "player_stats": "",
    "restart_data": "",
    "accounts_usage": "",
    "match_logs": ""
}

#: Contains database parameters.
database = {
    "url": "",
    "cluster": "",
    "accounts": "",
    "jaeger_cal": "",
    "collections": _collections
}

#: Contains url for base images.
base_images = dict()


## Methods

def get_config(launch_str: str):
    """
    Populate the config data from the config file.

    :param launch_str: Config file suffix. Useful to have different configurations files.
    """
    global LAUNCH_STR
    global GAPI_JSON
    LAUNCH_STR = launch_str
    GAPI_JSON = f"google_api_secret{launch_str}.json"

    file = f"{pathlib.Path(__file__).parent.absolute()}/../config{launch_str}.cfg"

    if not os.path.isfile(file):
        raise ConfigError(f"{file} not found!")

    config = ConfigParser(inline_comment_prefixes="#")
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
    # skip_api_test = True
    # if not skip_api_test:
    #     url = f"http://census.daybreakgames.com/s:{general['api_key']}/get/ps2:v2/faction"
    #     j_data = loads(get(url).content)
    #     if 'error' in j_data:
    #         raise ConfigError(
    #             f"Incorrect api key: {general['api_key']} in '{file}'")

    # Teamspeak section
    try:
        _check_section(config, "Teamspeak", file)
    except ConfigError:
        pass
    else:
        for key in ts:
            try:
                if key == "matches":
                    tmp = config['Teamspeak'][key].split(',')
                    ts[key].clear()
                    for m in tmp:
                        ts[key].append(list())
                        c_id = m.split('/')
                        for val in c_id:
                            ts[key][-1].append(int(val))
                elif isinstance(ts[key], int):
                    ts[key] = int(config['Teamspeak'][key])
                else:
                    ts[key] = config['Teamspeak'][key]
            except KeyError:
                _error_missing(key, 'Teamspeak', file)
            except ValueError:
                _error_incorrect(key, 'Teamspeak', file)


    # Channels section
    _check_section(config, "Channels", file)
    channels_list.clear()

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
    _check_section(config, "Base_Images", file)
    base_images.clear()

    for key in config['Base_Images'].keys():
        try:
            base_images[base_to_id[key]] = config['Base_Images'][key]
        except KeyError:
            raise ConfigError(f"Missing base '{key}' in 'base_to_id' dictionary in 'config.py'")


def _check_section(config, section, file):
    if section not in config:
        raise ConfigError(f"Missing section '{section}' in '{file}'")


def _error_missing(field, section, file):
    raise ConfigError(f"Missing field '{field}' in '{section}' in '{file}'")


def _error_incorrect(field, section, file):
    raise ConfigError(f"Incorrect field '{field}' in '{section}' in '{file}'")
