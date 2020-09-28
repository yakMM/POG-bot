from modules.ts3 import getTs3Bots
from matches import which_bot, which_team_channels
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