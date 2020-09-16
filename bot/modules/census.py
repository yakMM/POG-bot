from modules.asynchttp import apiRequestAndRetry as httpRequest
from modules.exceptions import ApiNotReachable, ElementNotFound
from classes.weapons import getWeapon
from modules.display import channelSend
import modules.config as cfg
from logging import getLogger

log = getLogger(__name__)

async def processScore(match):
    igDict = dict()
    start = match.startStamp
    end = start+cfg.ROUND_LENGHT*60
    for tm in match.teams:
        for aPlayer in tm.players:
            igDict[aPlayer.igId] = aPlayer
    for aPlayer in igDict.values():
        url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/characters_event/?character_id=' + \
        f'{aPlayer.igId}&type=KILL&after={start}&before={end}&c:limit=500'
        jdata = await httpRequest(url)
        if jdata["returned"] == 0:
            log.error(f'No kill found for player: id={aPlayer.igName} (url={url})')
            continue

        # Loop through all events
        event_list = jdata["characters_event_list"]
        for event in event_list:
            opoId = int(event["character_id"])
            if opoId not in igDict:
                # interaction with outside player, to be ignored
                continue
            opo = igDict[opoId]
            weapId = int(event["attacker_weapon_id"])
            try:
                weapon = getWeapon(weapId)
            except ElementNotFound:
                log.error(f'Weapon not found in database: id={weapId}')
                weapon = getWeapon(0)
            if opo is aPlayer:
                aPlayer.addOneSuicide()
            elif opo.team is aPlayer.team:
                aPlayer.addOneTK()
                opo.addOneDeath(0)
            else:
                if not weapon.isBanned:
                    pts = weapon.points
                    aPlayer.addOneKill(pts)
                    opo.addOneDeath(pts)
                else:
                    aPlayer.addIllegalWeapon(weapon.id)
                    # TODO: Should we add penalty?
        for weapId in aPlayer.illegalWeapons.keys():
            weapon = getWeapon(weapId)
            await channelSend("SC_ILLEGAL_WE",  match.id, aPlayer.mention, weapon.name,
                                                match.number, aPlayer.illegalWeapons[weapId])
            await channelSend("SC_ILLEGAL_WE",  cfg.channels["staff"], aPlayer.mention, weapon.name,
                                                match.number, aPlayer.illegalWeapons[weapId])

    await getCaptures(match, start, end)

async def getCaptures(match, start, end):
    factionDict = dict()
    for tm in match.teams:
        factionDict[tm.faction] = tm
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/world_event/' + \
            f'?world_id=19&after={start}&before={end}&c:limit=500'
    jdata = await httpRequest(url)
    if jdata["returned"] == 0:
        log.warning(f'No event found for map! (url={url})')
        return

    event_list = jdata["world_event_list"]
    baseOwner = None
    # Loop through all events from older to newer
    for event in event_list[::-1]:
        baseId = int(event["facility_id"])
        if baseId != match.map.id:
            # Not match base, to be ignored
            continue
        faction = int(event["faction_new"])
        if faction not in factionDict:
            continue
        capper = factionDict[faction]
        if baseOwner is None:
            # First cap
            capper.addCap(cfg.scores["capture"])
            baseOwner = capper
        if baseOwner is not capper:
            # Re cap
            capper.addCap(cfg.scores["recapture"])
            baseOwner = capper

async def getOfflinePlayers(team):
    if getOfflinePlayers.bypass:
        return list()
    igDict = dict()
    for p in team.players:
        igDict[p.igId] = p
    idString = ",".join(str(igId) for igId in igDict.keys())
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/characters_online_status/?character_id={idString}'
    jdata = await httpRequest(url)
    if jdata["returned"] == 0:
        raise ApiNotReachable(f"Empty answer on online_status call (url={url})")

    charList = jdata["characters_online_status_list"]

    offlinePlayers = list()

    for char in charList:
        if char["online_status"] == "0":
            offlinePlayers.append(igDict[int(char["character_id"])])

    return offlinePlayers

getOfflinePlayers.bypass = False