from general.exceptions import ElementNotFound
from general.enumerations import MatchStatus
from modules.database import get_one_item

from classes.bases import Base, MapSelection
from classes.teams import Team
from classes.audio_bot import AudioBot
from classes.accounts import AccountHander

from logging import getLogger

from match_process.player_picking import PlayerPicking
from match_process.faction_picking import FactionPicking
from match_process.base_picking import MapPicking
from match_process.base_selector import BaseSelector
from match_process.meta import Process

log = getLogger("pog_bot")


class Match:
    __bound_matches = dict()

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

    @classmethod
    def find_empty(cls):
        for match in cls.__bound_matches.values():
            if match.status is MatchStatus.IS_FREE:
                return match
        return None

    @classmethod
    async def get_from_database(cls, m_id: int):
        data = await get_one_item("matches", m_id)
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
    def is_picking_allowed(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound, no attribute 'is_picking_allowed'")
        try:
            self.__objects.get_process_attr("pick_status")
            return True
        except AttributeError:
            return False

    @property
    def base(self):
        return self.__data.base

    def spin_up(self, p_list):
        self.__objects.on_spin_up(p_list)

    def __getattr__(self, name):
        if not self.__objects:
            raise AttributeError(f"Match instance is not bound,\
                                  no attribute '{name}'")
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
        self.account_hander = None

    def on_spin_up(self, p_list):
        self.status = MatchStatus.IS_RUNNING
        self.base_selector = BaseSelector(self.proxy, base_pool=True)
        self.audio_bot = AudioBot(self.proxy)
        self.account_hander = AccountHander(self.proxy)
        self.data.id = self.account_hander.number
        self.current_process = PlayerPicking(self, p_list)

    def on_player_pick_over(self):
        self.status = MatchStatus.IS_RUNNING
        self.current_process = FactionPicking(self)

    def on_faction_pick_over(self):
        self.status = MatchStatus.IS_RUNNING
        self.current_process = MapPicking(self)

    def get_process_attr(self, name):
        if name in self.current_process.attributes:
            return self.current_process.attributes[name]
        else:
            raise AttributeError(f"Current process has no attribute '{name}'")

    def clean(self):
        self.data.clean()
        self.current_process = None
        self.base_selector = None
        self.audio_bot = None
        self.result_msg = None
        self.account_hander = None
        self.status = MatchStatus.IS_FREE

    @property
    def status_str(self):
        if not self.current_process:
            return MatchStatus.IS_FREE.value
        else:
            return self.current_process.status.value

    def __getattr__(self, name):
        try:
            return getattr(self.data, name)
        except AttributeError:
            raise AttributeError(f"'MatchObjects' object has no attribute '{name}'")
