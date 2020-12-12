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

log = getLogger("pog_bot")


class Match:

    __all_matches = dict()

    @classmethod
    def get(this, m_id):
        if id not in this.__all_matches:
            raise ElementNotFound(m_id)
        return this.__all_matches[m_id]

    @classmethod
    def init(this, client, list):
        for m_id in list:
            ch = client.get_channel(m_id)
            this.__all_matches[m_id] = this(m_id, ch)

    def __init__(self, m_id, ch, from_data = False):
        self.__id = m_id
        self.__players = dict()
        self.__teams = [None, None]
        self.__map_selector = None
        self.__result_msg = None
        self.__accounts = None
        self.__round_stamps = list()
        if from_data:
            self.__number = m_id
            return
        self.__number = 0
        self.__status = MatchStatus.IS_FREE
        self.__channel = ch
        self.__audio_bot = AudioBot(self)
    