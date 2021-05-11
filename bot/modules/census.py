"""
This module handles calculations from PS2 Census API
"""

# Imports:
from modules.asynchttp import api_request_and_retry as http_request, ApiNotReachable
import modules.config as cfg
from classes import Weapon
from display import AllStrings as display, ContextWrapper
from modules.tools import AutoDict

from logging import getLogger

log = getLogger("pog_bot")


async def process_score(match: 'match.classes.MatchData', start_time: int, match_channel: 'TextChannel' = None):
    """
    Calculate the result score for the MatchData object provided.

    :param match: MatchData object to fill with scores.
    :param start_time: Round start timestamp: will process score starting form this time.
    :param match_channel: Match channel for illegal weapons display (optional).
    :raise ApiNotReachable: If an API call fail.
    """
    # Temp data structures
    ig_dict = dict()
    current_ill_weapons = dict()

    # Start and end timestamps
    start = start_time
    end = start + (match.round_length * 60)

    # Fill player dictionary (in-game id -> player object)
    for tm in match.teams:
        for player in tm.players:
            if not player.is_disabled:
                ig_dict[int(player.ig_id)] = player

    # Request url:
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/characters_event/?character_id=' \
          f'{",".join(str(p.ig_id) for p in ig_dict.values())}&type=KILL&after={start}&before={end}&c:limit=500'
    j_data = await http_request(url, retries=5)

    if j_data["returned"] == 0:
        raise ApiNotReachable(f"Empty answer on score calculation (url={url})")

    event_list = j_data["characters_event_list"]

    ill_weapons = dict()

    # Loop through all events retrieved:
    for event in event_list:

        # Get opponent player
        oppo = ig_dict.get(int(event["character_id"]))
        if not oppo:
            # interaction with outside player, skip it
            continue
        opo_loadout = oppo.get_loadout(int(event["character_loadout_id"]))

        player = ig_dict.get(int(event["attacker_character_id"]))
        if not player:
            # interaction with outside player, skip it
            continue
        player_loadout = player.get_loadout(int(int(event["attacker_loadout_id"])))

        # Get weapon
        weap_id = int(event["attacker_weapon_id"])
        is_hs = int(event["is_headshot"]) == 1
        weapon = Weapon.get(weap_id)
        if not weapon:
            log.error(f'Weapon not found in database: id={weap_id}')
            weapon = Weapon.get(0)

        # Parse event into loadout objects
        if oppo is player:
            # Player killed themselves
            player_loadout.add_one_suicide()
        elif oppo.team is player.team:
            # Team-kill
            player_loadout.add_one_tk()
            opo_loadout.add_one_death(0)
        else:
            # Regular kill
            if not weapon.is_banned:
                # If weapon is allowed
                pts = weapon.points
                player_loadout.add_one_kill(pts, is_hs)
                opo_loadout.add_one_death(pts)
            else:
                # If weapon is banned, add it to illegal weapons list
                player_loadout.add_illegal_weapon(weapon.id)
                if player not in ill_weapons:
                    ill_weapons[player] = AutoDict()
                ill_weapons[player].auto_add(weapon.id, 1)

    # Display all banned-weapons uses for this player:
    for player in ill_weapons.keys():
        for weap_id in ill_weapons[player]:
            weapon = Weapon.get(weap_id)
            if match_channel:
                await display.SC_ILLEGAL_WE.send(match_channel, player.mention, weapon.name,
                                                 match.id, ill_weapons[player][weap_id])
                await display.SC_ILLEGAL_WE.send(ContextWrapper.channel(cfg.channels["staff"]), player.mention,
                                                 weapon.name, match.id, ill_weapons[player][weap_id])

    # Also get base captures
    await get_captures(match, start, end)


async def get_captures(match: 'match.classes.MatchData', start: int, end: int):
    """
    Find base captures for the MatchData object provided, between start and stop timestamps.

    :param match: MatchData object to fill with scores.
    :param start: Round start timestamp.
    :param end: Round end timestamp.
    :raise ApiNotReachable: If an API call fail.
    """
    faction_dict = dict()
    # Get teams factions (faction id -> team object)
    for tm in match.teams:
        faction_dict[tm.faction] = tm

    # URL to get events
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/world_event/' + \
          f'?world_id=19&after={start}&before={end}&c:limit=500'
    j_data = await http_request(url, retries=5)
    if j_data["returned"] == 0:
        # No event
        log.warning(f'No event found for base! (url={url})')
        return

    # Initialize event list
    event_list = j_data["world_event_list"]
    base_owner = None

    # Loop through all events from older to newer
    for event in event_list[::-1]:
        base_id = int(event["facility_id"])
        if base_id != match.base.id:
            # Not match base, skip
            continue
        faction = int(event["faction_new"])
        if faction not in faction_dict:
            # Faction unrelated to the match, skip
            continue

        capper = faction_dict[faction]  # Who just captured the base
        if base_owner is None:
            # First cap
            capper.add_cap(cfg.scores["capture"])
            base_owner = capper
        elif base_owner is not capper:
            # Re cap
            capper.add_cap(cfg.scores["recapture"])
            base_owner = capper


async def get_offline_players(team: 'classes.Team') -> list:
    """
    Find all offline players for the team provided

    :param team: Team to investigate.
    :return: List of offline players
    :raise ApiNotReachable: If the API call fail.
    """
    # Assemble a string of all players in-game IDs
    ig_dict = dict()
    for p in team.players:
        if not p.is_benched:
            ig_dict[p.ig_id] = p
    id_string = ",".join(str(ig_id) for ig_id in ig_dict.keys())

    # DO the request
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/characters_online_status/' \
          f'?character_id={id_string}'
    j_data = await http_request(url)
    if j_data["returned"] == 0:
        raise ApiNotReachable(f"Empty answer on online_status call (url={url})")

    # Load the results
    char_list = j_data["characters_online_status_list"]

    # Will contain offline players
    offline_players = list()

    # Iterate through players
    for char in char_list:
        if char["online_status"] == "0":
            # If online, add to list
            offline_players.append(ig_dict[int(char["character_id"])])

    return offline_players

