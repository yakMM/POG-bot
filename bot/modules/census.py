# @CHECK 2.0 features OK

from modules.asynchttp import api_request_and_retry as http_request, ApiNotReachable
from classes.weapons import Weapon
from display.strings import AllStrings as display
from display.classes import ContextWrapper
import modules.config as cfg
from logging import getLogger

log = getLogger("pog_bot")


async def process_score(match):
    ig_dict = dict()
    start = match.start_stamp
    end = start + cfg.general['round_length'] * 60
    for tm in match.teams:
        for a_player in tm.players:
            ig_dict[a_player.ig_id] = a_player
    for a_player in ig_dict.values():
        url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/characters_event/?character_id=' + \
        f'{a_player.ig_id}&type=KILL&after={start}&before={end}&c:limit=500'
        jdata = await http_request(url)
        if jdata["returned"] == 0:
            log.error(f'No kill found for player: id={a_player.ig_name} (url={url})')
            continue

        # Loop through all events
        event_list = jdata["characters_event_list"]
        for event in event_list:
            opo_id = int(event["character_id"])
            if opo_id not in ig_dict:
                # interaction with outside player, to be ignored
                continue
            opo = ig_dict[opo_id]
            weap_id = int(event["attacker_weapon_id"])
            weapon = Weapon.get(weap_id)
            if not weapon:
                log.error(f'Weapon not found in database: id={weap_id}')
                weapon = Weapon.get(0)
            if opo is a_player:
                a_player.add_one_suicide()
            elif opo.team is a_player.team:
                a_player.add_one_t_k()
                opo.add_one_death(0)
            else:
                if not weapon.is_banned:
                    pts = weapon.points
                    a_player.add_one_kill(pts)
                    opo.add_one_death(pts)
                else:
                    a_player.add_illegal_weapon(weapon.id)
                    # TODO: Should we add penalty?
        for weap_id in a_player.illegal_weapons.keys():
            weapon = Weapon.get(weap_id)
            await display.SC_ILLEGAL_WE.send(match.channel, a_player.mention, weapon.name,
                                                match.number, a_player.illegal_weapons[weap_id])
            await display.SC_ILLEGAL_WE.send(ContextWrapper.channel(cfg.channels["staff"]), a_player.mention, weapon.name,
                                                match.number, a_player.illegal_weapons[weap_id])

    await get_captures(match, start, end)


async def get_captures(match, start, end):
    faction_dict = dict()
    for tm in match.teams:
        faction_dict[tm.faction] = tm
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/world_event/' + \
            f'?world_id=19&after={start}&before={end}&c:limit=500'
    jdata = await http_request(url)
    if jdata["returned"] == 0:
        log.warning(f'No event found for base! (url={url})')
        return

    event_list = jdata["world_event_list"]
    base_owner = None
    # Loop through all events from older to newer
    for event in event_list[::-1]:
        base_id = int(event["facility_id"])
        if base_id != match.base.id:
            # Not match base, to be ignored
            continue
        faction = int(event["faction_new"])
        if faction not in faction_dict:
            continue
        capper = faction_dict[faction]
        if base_owner is None:
            # First cap
            capper.add_cap(cfg.scores["capture"])
            base_owner = capper
        if base_owner is not capper:
            # Re cap
            capper.add_cap(cfg.scores["recapture"])
            base_owner = capper


async def get_offline_players(team):
    ig_dict = dict()
    for p in team.players:
        ig_dict[p.ig_id] = p
    id_string = ",".join(str(ig_id) for ig_id in ig_dict.keys())
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/characters_online_status/?character_id={id_string}'
    j_data = await http_request(url)
    if j_data["returned"] == 0:
        raise ApiNotReachable(f"Empty answer on online_status call (url={url})")

    char_list = j_data["characters_online_status_list"]

    offline_players = list()

    for char in char_list:
        if char["online_status"] == "0":
            offline_players.append(ig_dict[int(char["character_id"])])

    return offline_players

