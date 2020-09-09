""" Retrieves configuration from the config file
"""

from json import loads
from requests import get
from configparser import ConfigParser, ParsingError
from modules.exceptions import ConfigError

# DiscordIds
discord_ids = {
    "lobby": 0,
    "register": 0,
    "matches": list(),
    "results": 0,
    "rules": 0,
    "rules_msg": 0,
    "admin_role": 0,
    "info_role": 0,
    "registered_role": 0,
    "notify_role": 0
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
    "players_drop_channel": ""
}

# General

general = {
    "token": "",
    "api_key": "",
    "command_prefix": "",
    "lobby_size": 0,
    "sinusbot_user": "",
    "sinusbot_pass": "",
    "jaeger_cal": "",
    "map_pool": list()
}

AFK_TIME = 20  # minutes
ROUND_LENGTH = 1  # minutes
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

# PIL_MAPS_IDS -- no longer used -- = [3430, 302030, 239000, 305010, 230, 307010]  # peris, acan, pale, ghanan, xeno, chac

# PIL map images, these should be added to config file I think
map_pool_images = {"Acan Southern Labs": "https://i.imgur.com/IhF9wQN.png",
                   "Chac Fusion Lab": "https://i.imgur.com/XQ5YERh.jpeg",
                   "Ghanan Southern Crossing": "https://i.imgur.com/3GEEcx7.png",
                   "Pale Canyon Chemical": "https://i.imgur.com/JuRQrQm.png",
                   "Peris Eastern Grove": "https://i.imgur.com/2yoMxU2.jpeg",
                   "Rashnu Watchtower": "https://i.imgur.com/9RkkmFQ.jpeg",
                   "XenoTech Labs": "https://i.imgur.com/uIc2NJH.png"}

# Database

_collections = {
    "users": "",
    "sBases": ""
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
        raise ConfigError(f"Parsing Error in '{file}'\n{e}")

    # General section
    _checkSection(config, "General", file)

    for key in general:
        try:
            if key == "map_pool":
                tmp = config['General'][key].split(',')
                general[key].clear()
                for map in tmp:
                    general[key].append(map)
            else:
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

    # Teamspeak_Ids section
    _checkSection(config, "Teamspeak_Ids", file)

    for key in teamspeak_ids:
        try:
            teamspeak_ids[key] = config['Teamspeak_Ids'][key]
        except KeyError:
            _errorMissing(key, 'Teamspeak_Ids', file)
        except ValueError:
            _errorIncorrect(key, 'Teamspeak_Ids', file)

    # Audio_Ids section
    _checkSection(config, "Audio_Ids", file)

    for key in audio_ids:
        try:
            audio_ids[key] = config['Audio_Ids'][key]
        except KeyError:
            _errorMissing(key, 'Audio_Ids', file)
        except ValueError:
            _errorIncorrect(key, 'Audio_Ids', file)

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
    VERSION = txt_str[3:-2]  # Extracts "X.X.X" from string "# vX.X.X:" in a lazy way


def _checkSection(config, section, file):
    if section not in config:
        raise ConfigError(f"Missing section '{section}' in '{file}'")


def _errorMissing(field, section, file):
    raise ConfigError(f"Missing field '{field}' in '{section}' in '{file}'")


def _errorIncorrect(field, section, file):
    raise ConfigError(f"Incorrect field '{field}' in '{section}' in '{file}'")
