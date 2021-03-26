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
    IS_PLAYING = "Match is being played"
    IS_RESULT = "Result"

