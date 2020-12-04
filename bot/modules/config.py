""" Retrieves configuration from the config file
"""

from json import loads
from requests import get
from configparser import ConfigParser, ParsingError
from modules.exceptions import ConfigError
import logging

# STATIC PARAMETERS:
AFK_TIME = 15  # minutes
ROUND_LENGTH = 0.09  # minutes

# DYNAMIC PARAMETERS:
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

channels_list = list()

roles = {
    "admin": 0,
    "info": 0,
    "registered": 0,
    "notify": 0
}

# TeamspeakIds
teamspeak_ids = {
    "ts_lobby": "",
    "ts_afk": "",
    "ts_match_1_picks": "",
    "ts_match_1_team_1": "",
    "ts_match_1_team_2": "",
    "ts_match_2_picks": "",
    "ts_match_2_team_1": "",
    "ts_match_2_team_2": "",
}

# AudioIds
audio_ids = {
    "round_over": "",
    "select_factions": "",
    "select_map": "",
    "select_teams": "",
    "team_1_nc": "",
    "team_1_tr": "",
    "team_1_vs": "",
    "team_2_nc": "",
    "team_2_tr": "",
    "team_2_vs": "",
    "type_ready": "",
    "5s": "",
    "10s": "",
    "30s": "",
    "drop_match_1_picks": "",
    "drop_match_2_picks": "",
    "drop_match_3_picks": "",
    "factions_selected": "",
    "gelos_in_prison": "",
    "map_selected": "",
    "players_drop_channel": "",
    "switch_sides": ""
}

# General

general = {
    "token": "",
    "api_key": "",
    "command_prefix": "",
    "lobby_size": 0,
    "sinusbot_user": "",
    "sinusbot_pass": "",
    "rules_msg_id": 0
}

scores = {
    "teamkill": 0,
    "suicide": 0,
    "capture": 0,
    "recapture": 0
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
facility_suffix = {
    2: "Amp Station",
    3: "Bio Lab",
    4: "Tech Plant"
}

# PIL map images, these should be added to config file I think
map_pool_images = {"Acan Southern Labs": "https://i.imgur.com/IhF9wQN.png",
                   "Chac Fusion Lab": "https://i.imgur.com/XQ5YERh.jpeg",
                   "Ghanan Southern Crossing": "https://i.imgur.com/3GEEcx7.png",
                   "Pale Canyon Chemical": "https://i.imgur.com/JuRQrQm.png",
                   "Peris Eastern Grove": "https://i.imgur.com/2yoMxU2.jpeg",
                   "Rashnu Watchtower": "https://i.imgur.com/9RkkmFQ.jpeg",
                   "XenoTech Labs": "https://i.imgur.com/REGEX_uIc2NJH.png"}

# Database

_collections = {
    "users": "",
    "s_bases": "",
    "s_weapons" : "",
    "matches" : ""
}

database = {
    "url": "",
    "cluster": "",
    "accounts": "",
    "jaeger_cal": "",
    "collections": _collections
}


# Methods


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
    # url = f"http://census.daybreakgames.com/s:{general['api_key']}/get/ps2:v2/faction"
    # jdata = loads(get(url).content)
    # if 'error' in jdata:
    #     raise ConfigError(
    #         f"Incorrect api key: {general['api_key']} in '{file}'")

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

    # Teamspeak_Ids section
    _check_section(config, "Teamspeak_Ids", file)

    for key in teamspeak_ids:
        try:
            teamspeak_ids[key] = config['Teamspeak_Ids'][key]
        except KeyError:
            _error_missing(key, 'Teamspeak_Ids', file)
        except ValueError:
            _error_incorrect(key, 'Teamspeak_Ids', file)

    # Audio_Ids section
    _check_section(config, "Audio_Ids", file)

    for key in audio_ids:
        try:
            audio_ids[key] = config['Audio_Ids'][key]
        except KeyError:
            _error_missing(key, 'Audio_Ids', file)
        except ValueError:
            _error_incorrect(key, 'Audio_Ids', file)

    # Roles section
    _check_section(config, "Roles", file)
    for key in roles:
        try:
            roles[key] = int(config['Roles'][key])
        except KeyError:
            _error_missing(key, 'Roles', file)
        except ValueError:
            _error_incorrect(key, 'Roles', file)

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
    try:
        with open('../CHANGELOG.md', 'r', encoding='utf-8') as txt:
            txt_str = txt.readline()
        global VERSION
        # Extracts "X.X.X" from string "# vX.X.X:" in a lazy way
        VERSION = txt_str[3:-2]
    except Exception as e:
        logging.warning(f"Error readying CHANGELOG.md. Did you remember to call this module from the root level?\n{e}\n"
                        f"If you ran ts3.py just ignore this error...")


def _check_section(config, section, file):
    if section not in config:
        raise ConfigError(f"Missing section '{section}' in '{file}'")


def _error_missing(field, section, file):
    raise ConfigError(f"Missing field '{field}' in '{section}' in '{file}'")


def _error_incorrect(field, section, file):
    raise ConfigError(f"Incorrect field '{field}' in '{section}' in '{file}'")
