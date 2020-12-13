import modules.config as cfg
from modules.exceptions import UnexpectedError, AccountsNotEnough, \
    ElementNotFound, UserLackingPermission, AlreadyPicked
from display import SendCtx, send
from modules.enumerations import PlayerStatus, MatchStatus, SelStatus
from modules.image_maker import publish_match_image
from modules.census import process_score, get_offline_players
from modules.database import update_match
from datetime import datetime as dt, timezone as tz
from modules.ts_interface import AudioBot
from modules.reactions import ReactionHandler, add_handler

from classes.teams import Team  # ok
from classes.players import TeamCaptain, ActivePlayer  # ok
from classes.maps import MapSelection, main_maps_pool  # ok
from classes.accounts import AccountHander  # ok

from random import choice as random_choice
from lib.tasks import loop
from asyncio import sleep
from logging import getLogger

from match_process.player_picking import PlayerPicking

log = getLogger("pog_bot")


class Match:

    __all_matches = dict()

    @classmethod
    def get(this, m_id):
        if m_id not in this.__all_matches:
            raise ElementNotFound(m_id)
        return this.__all_matches[m_id]

    @classmethod
    def init(this, client, ch_list):
        for m_id in ch_list:
            ch = client.get_channel(m_id)
            this.__all_matches[m_id] = this(m_id, ch)
            print(f"Adding: {m_id}")

    @classmethod
    def find_empty(this):
        for match in this.__all_matches.values():
            if match.status is MatchStatus.IS_FREE:
                return match
        return None

    def __init__(self, m_id, ch):
        self.__id = m_id
        self.__channel = ch
        self.__cp = None
        self.__currentProcess = None

    @property
    def id(self):
        return self.__id

    @property
    def channel(self):
        return self.__channel

    # @property
    # def msg(self):
    #     return self.__cp.result_msg

    # @property
    # def status(self):
    #     return self.__status



    # @property
    # def teams(self):
    #     return self.__cp.teams

    # @property
    # def status_string(self):
    #     return self.__status.value

    # @property
    # def number(self):
    #     return self.__number

    def spin_up(self, p_list):
        self.__cp.status = MatchStatus.IS_RUNNING
        self.__currentProcess = PlayerPicking(self.__cp, p_list)


class MatchContentProxy:

    def __init__(self, match):
        self.match = match
        self.id = match.id
        self.channel = match.channel
        self.teams = [None, None]
        self.map_selector = None
        self.result_msg = None
        self.accounts = None
        self.round_stamps = list()
        self.number = 0
        self.status = MatchStatus.IS_FREE
        self.audio_bot = AudioBot(self)