from modules.ts3 import getTs3Bots
import modules.config as cfg

from asyncio import sleep

# @TODO: TEMP

def factionAudio(team):      
    audio_string = f"team_{team.id+1}_{cfg.factions[team.faction].lower()}"
    ts3bot = which_bot(team.match.id)
    ts3bot.enqueue(cfg.audio_ids[audio_string])


async def mapAudio(match):
    ts3bot = which_bot(match.id)
    # ts3: map selected
    ts3bot.enqueue(cfg.audio_ids["map_selected"])
    # ts3: players drop to team channels
    await sleep(ts3bot.get_duration(cfg.audio_ids["map_selected"]))
    ts3bot.enqueue(cfg.audio_ids["players_drop_channel"])
    # ts3: move bots to team channels:
    await sleep(ts3bot.get_duration(cfg.audio_ids["players_drop_channel"]))
    team_channels = which_team_channels(match.id)
    getTs3Bots()[0].move(team_channels[0])
    getTs3Bots()[1].move(team_channels[1])


def which_bot(match_id):
    if match_id == cfg.channels["matches"][0]:
        ts3bot = getTs3Bots()[0]
    elif match_id == cfg.channels["matches"][1] or match_id == cfg.channels["matches"][2]:
        ts3bot = getTs3Bots()[1]
    return ts3bot


def which_pick_channels(match_id):
    pick_channel = ""
    for i in range(0, 3):
        if match_id == cfg.channels["matches"][i]:
            pick_channel = cfg.teamspeak_ids[f"ts_match_{i+1}_picks"]
    return pick_channel


def which_team_channels(match_id):
    team_channels = ("", "")
    for i in range(0, 3):
        if match_id == cfg.channels["matches"][i]:
            team_channels = (cfg.teamspeak_ids[f"ts_match_{i+1}_team_1"], cfg.teamspeak_ids[f"ts_match_{i+1}_team_2"])
    return team_channels