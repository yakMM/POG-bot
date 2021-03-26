"""Custom enumerations classes to define status of the objects
"""

from enum import Enum


class MatchStatus(Enum):
    IS_FREE = "No match"
    IS_RUNNING = "Processing..."
    IS_PICKING = "Waiting for captains to pick players"
    IS_FACTION = "Waiting for captains to pick factions"
    IS_BASING = "Waiting for base pick"
    IS_WAITING = "Waiting for teams"
    IS_STARTING = "Match starting"
    IS_PLAYING = "Match is being played"
    IS_RESULT = "Result"


# class PlayerStatus(Enum):
#     IS_NOT_REGISTERED = 0
#     IS_REGISTERED = 1
#     IS_LOBBIED = 2
#     IS_MATCHED = 3
#     IS_PICKED = 4
#     IS_WAITING = 5
#     IS_PLAYING = 6
