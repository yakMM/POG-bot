from general.exceptions import ElementNotFound
from general.enumerations import MatchStatus

from classes.bases import Base
from classes.teams import Team
from classes.audio_bot import AudioBot

from logging import getLogger

from lib.tasks import loop

from display.strings import AllStrings as disp

import modules.database as db
import modules.roles
import modules.accounts_handler as accounts

from match_process.player_picking import PlayerPicking
from match_process.faction_picking import FactionPicking
from match_process.base_picking import MapPicking
from match_process.getting_ready import GettingReady
from match_process.base_selector import BaseSelector
from match_process.meta import Process

log = getLogger("pog_bot")


class Match:
    __bound_matches = dict()
    _last_match_id = 0

    @classmethod
    def get(cls, m_id: int):
        if m_id not in cls.__bound_matches:
            raise ElementNotFound(m_id)
        return cls.__bound_matches[m_id]

    @classmethod
    def init_channels(cls, client, ch_list: list):
        for ch_id in ch_list:
            channel = client.get_channel(ch_id)
            instance = cls()
            instance.bind(channel)
            cls.__bound_matches[ch_id] = instance
        cls._last_match_id = db.get_specific("restart_data", 0, "last_match_id")

    @classmethod
    def find_empty(cls):
        for match in cls.__bound_matches.values():
            if match.status is MatchStatus.IS_FREE:
                return match
        return None

    @classmethod
    async def get_from_database(cls, m_id: int):
        data = await db.async_db_call(db.get_element, "matches", m_id)
        instance = cls(data)
        return instance

    def __init__(self, data=None):
        self.__data = MatchData(self, data)
        self.__objects = None

    def bind(self, channel):
        self.__objects = MatchObjects(self, self.__data, channel)

    @property
    def channel(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound,\
                                  no attribute 'channel'")
        return self.__objects.channel

    @property
    def base_selector(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'match_selector'")
        return self.__objects.base_selector

    @property
    def status(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'status'")
        return self.__objects.status

    @property
    def next_status(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'status'")
        return self.__objects.next_status

    @property
    def status_str(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'status_str'")
        return self.__objects.status_str

    @property
    def number(self):
        return self.__data.id

    @property
    def teams(self):
        return self.__data.teams

    @property
    def round_no(self):
        return self.__data.round_no

    @property
    def is_started(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'is_started'")
        if self.next_status in (MatchStatus.IS_PLAYING, MatchStatus.IS_RESULT):
            return True
        return False

    @property
    def is_picking_allowed(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'is_picking_allowed'")
        if self.status is MatchStatus.IS_RUNNING:
            return False
        try:
            self.__objects.get_process_attr("pick_status")
            return True
        except AttributeError:
            return False

    @property
    def base(self):
        return self.__data.base

    def spin_up(self, p_list):
        Match._last_match_id += 1
        self.__objects.on_spin_up(p_list)
        db.update_element("restart_data", 0, {"last_match_id": Match._last_match_id})

    def __getattr__(self, name):
        if not self.__objects:
            raise AttributeError(f"Match instance is not bound, no attribute '{name}'")
        return self.__objects.get_process_attr(name)


class MatchData:
    def __init__(self, match: Match, data: dict):
        self.match = match
        if data:
            self.id = data["_id"]
            self.teams = [Team.from_data(self.match, 0, data["teams"][0]), Team.from_data(self.match, 1, data["teams"][1])]
            self.base = Base.get(data["base_id"])
            self.round_stamps = data["round_stamps"]
        else:
            self.id = 0
            self.teams = [None, None]
            self.base = None
            self.round_stamps = list()

    def clean(self):
        # Clean players if in teams
        for tm in self.teams:
            if tm is not None:
                tm.clean()

        self.id = 0
        self.teams = [None, None]
        self.base = None
        self.round_stamps = list()

    @property
    def round_no(self):
        if self.match.status is MatchStatus.IS_PLAYING:
            return len(self.round_stamps)
        if self.match.status in (MatchStatus.IS_STARTING, MatchStatus.IS_WAITING):
            return len(self.round_stamps) + 1
        return 0


class MatchObjects:
    def __init__(self, match: Match, data: MatchData, channel: int):
        self.status = MatchStatus.IS_FREE
        self.data = data
        self.proxy = match
        self.channel = channel
        self.current_process = None
        self.base_selector = None
        self.audio_bot = None
        self.result_msg = None
        self.clean_channel.start()
        self.players_with_account = list()

    def on_spin_up(self, p_list):
        self.data.id = Match._last_match_id
        self.clean_channel.cancel()
        self.status = MatchStatus.IS_RUNNING
        self.base_selector = BaseSelector(self, base_pool=True)
        self.audio_bot = AudioBot(self.proxy)
        self.current_process = PlayerPicking(self, p_list)

    def on_player_pick_over(self):
        self.status = MatchStatus.IS_RUNNING
        self.current_process = FactionPicking(self)

    def on_faction_pick_over(self):
        self.status = MatchStatus.IS_RUNNING
        self.current_process = MapPicking(self)

    def on_base_pick_over(self):
        self.status = MatchStatus.IS_RUNNING
        self.current_process = GettingReady(self)

    def get_process_attr(self, name):
        if name in self.current_process.attributes:
            return self.current_process.attributes[name]
        else:
            raise AttributeError(f"Current process has no attribute '{name}'")

    async def clean(self):
        await self.base_selector.clean()
        for a_player in self.players_with_account:
            await accounts.terminate_account(a_player)
        self.data.clean()
        self.current_process = None
        self.players_with_account = list()
        self.base_selector = None
        self.audio_bot = None
        self.result_msg = None
        self.status = MatchStatus.IS_FREE
        self.clean_channel.start()

    @loop(count=1)
    async def clean_channel(self):
        await disp.MATCH_CHANNEL_OVER.send(self.channel)
        await modules.roles.modify_match_channel(self.match.channel, view=False)

    @property
    def status_str(self):
        return self.next_status.value

    @property
    def next_status(self):
        if not self.current_process:
            return MatchStatus.IS_FREE
        else:
            return self.current_process.status

    def __getattr__(self, name):
        try:
            return getattr(self.data, name)
        except AttributeError:
            raise AttributeError(f"'MatchObjects' object has no attribute '{name}'")
