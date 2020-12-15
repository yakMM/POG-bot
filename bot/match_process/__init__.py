from modules.exceptions import ElementNotFound
from modules.enumerations import MatchStatus
from modules.database import get_one_item


from classes.maps import Map, MapSelection
from classes.teams import Team
from classes.audio_bot import AudioBot
from classes.accounts import AccountHander

from logging import getLogger

from match_process.player_picking import PlayerPicking

log = getLogger("pog_bot")


class Match:

    __bound_matches = dict()

    @classmethod
    def get(this, m_id : int):
        if m_id not in this.__bound_matches:
            raise ElementNotFound(m_id)
        return this.__bound_matches[m_id]

    @classmethod
    def init_channels(this, client, ch_list : list):
        for ch_id in ch_list:
            channel = client.get_channel(ch_id)
            instance = this()
            instance.bind(channel)
            this.__bound_matches[ch_id] = instance

    @classmethod
    def find_empty(this):
        for match in this.__bound_matches.values():
            if match.status is MatchStatus.IS_FREE:
                return match
        return None

    @classmethod
    async def get_from_database(this, m_id : int):
        data = await get_one_item("matches", m_id)
        instance = this(data)
        return instance

    def __init__(self, data=None):
        self.__data = MatchData(self, data)
        self.__objects = None
        self.__currentProcess = None

    def bind(self, channel):
        self.__objects = MatchObjects(self, channel)

    @property
    def channel(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound,\
                                  no attribute 'channel'")
        return self.__objects.channel

    @property
    def status(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound,\
                                  no attribute 'status'")
        return self.__objects.status

    @property
    def status_str(self):
        if not self.__objects:
            raise AttributeError("Match instance is not bound,\
                                  no attribute 'status_str'")
        return self.__objects.status.value

    @property
    def number(self):
        return self.__data.id

    @property
    def teams(self):
        return self.__data.teams

    def spin_up(self, p_list):
        self.__objects.status = MatchStatus.IS_RUNNING
        self.__objects.init()
        self.__currentProcess = PlayerPicking(self, self.__objects,\
                                              self.__data, p_list)


class MatchObjects:
    def __init__(self, match, channel):
        self.status = MatchStatus.IS_FREE
        self.match = match
        self.channel = channel
        self.map_selector = None
        self.audio_bot = None
        self.result_msg = None
        self.account_hander = None

    def init(self):
        self.map_selector = MapSelection(self.match, map_pool=True)
        self.audio_bot = AudioBot(self.match)
        self.account_hander = AccountHander(self.match)

class MatchData:
    def __init__(self, match, data):
        self.match = match
        if data:
            self.id = data["_id"]
            self.teams = [Team.from_data(self.match, 0, data["teams"][0]),\
                          Team.from_data(self.match, 1, data["teams"][1])]
            self.map = Map.get(data["base_id"])
            self.round_stamps = data["round_stamps"]
        else:
            self.id = 0
            self.teams = [None, None]
            self.map = None
            self.round_stamps = list()
