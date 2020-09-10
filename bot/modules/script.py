from modules.asynchttp import request
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
        jdata = await request(url)
        try:
            if jdata["returned"] == 0:
                log.error(f'No kill found for player: id={aPlayer.igName} (url={url})')
                #raise ApiEmptyAnswer(url)
        except KeyError:
            raise ApiNotReachable(url)
        
        # Loop through all events
        event_list = jdata["characters_event_list"]
        for event in event_list:
            opoId = event["character_id"]
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
                    await channelSend("SC_ILLEGAL_WE", cfg.channels["staff"], aPlayer.mention, weapon.name, match.number)
                    # TODO: Should we add penalty?
    await getCaptures(match, start, end)

async def getCaptures(match, start, end):
    factionDict = dict()
    for tm in match.teams:
        factionDict[tm.faction] = tm
    url = f'http://census.daybreakgames.com/s:{cfg.general["api_key"]}/get/ps2:v2/world_event/' + \
            f'?world_id=19&after={start}&before={end}&c:limit=500'
    jdata = await request(url)
    try:
        if jdata["returned"] == 0:
            log.error(f'No event found for map! (url={url})')
            # raise ApiEmptyAnswer(url)
    except KeyError:
        raise ApiNotReachable(url)
    event_list = jdata["world_event_list"]

    baseOwner = None
    # Loop through all events from older to newer
    for event in event_list[::-1]:
        baseId = int(event["facility_id"])
        if baseId != match.map.id:
            # Not match base, to be ignored
            continue
        capper = factionDict[int(event["faction_new"])]
        if baseOwner is None:
            # First cap
            capper.addCap(cfg.scores["capture"])
            baseOwner = capper
        if baseOwner is not capper:
            # Re cap
            capper.addCap(cfg.scores["recapture"])
            baseOwner = capper

