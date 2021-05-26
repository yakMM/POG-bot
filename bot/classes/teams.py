# @CHECK 2.0 features OK

""" Basic team object, should be explicit
"""

from .scores import TeamScore
from match import MatchStatus


class Team:
    def __init__(self, id, name, match):
        self.__id = id
        self.__name = name
        self.__players = list()
        self.__faction = 0
        self.__match = match
        self.__is_playing = False
        self.__team_score = None
        self.__is_turn = False

    @property
    def id(self):
        return self.__id

    def get_data(self):
        return self.__team_score.get_data()

    @property
    def ig_string(self):
        p_string = ",".join(p.ig_name for p in self.__players)
        return f"{self.__name}: `{p_string}`"

    @property
    def name(self):
        return self.__name

    @property
    def players(self):
        return self.__players

    @property
    def faction(self):
        return self.__faction

    @faction.setter
    def faction(self, faction):
        self.__faction = faction

    @property
    def team_score(self):
        return self.__team_score

    @property
    def is_playing(self):
        return self.__is_playing

    @property
    def player_pings(self):
        # Excluding captain
        if self.match.next_status in (MatchStatus.IS_WAITING, MatchStatus.IS_STARTING, MatchStatus.IS_PLAYING):
            return [f"- {'~~' if p.is_benched else ''}{p.mention} ({p.name}) [{p.ig_name}]{'~~' if p.is_benched else ''}" for p in self.__players[1:]]
        else:
            return [f"- {'~~' if p.is_benched else ''}{p.mention} ({p.name}){'~~' if p.is_benched else ''}" for p in self.__players[1:]]

    @property
    def all_pings(self):
        # All players with captain
        pings = [p.mention for p in self.__players]
        return pings

    @property
    def captain(self):
        try:
            return self.__players[0]
        except IndexError:
            return None

    @property
    def is_players(self):
        return len(self.__players) > 1

    @property
    def match(self):
        return self.__match

    @property
    def is_turn(self):
        return self.__is_turn

    @is_turn.setter
    def is_turn(self, bl):
        self.__is_turn = bl

    def demote_captain(self):
        if len(self.__players) < 2:
            return False
        if self.__players[1].is_benched:
            return False
        else:
            self.__players.append(self.__players.pop(0))
            return True

    def on_player_bench(self, player):
        if player is self.__players[-1]:
            return
        else:
            self.__players.remove(player)
            self.__players.append(player)

    def is_captain(self, player):
        try:
            return player is self.__players[0]
        except IndexError:
            return False

    def on_team_ready(self, ready):
        self.__is_playing = ready
        for a_player in self.__players:
            a_player.on_team_ready(ready)

    def on_match_starting(self):
        if not self.__team_score:
            self.__team_score = TeamScore(self.id, self.match, self.name, self.faction)
            self.match.data.teams[self.__id] = self.__team_score
        for a_player in self.__players:
            a_player.on_match_starting()

    def clear(self):
        self.__players.clear()

    def clean(self):
        for a_player in self.__players:
            a_player.clean(team_clean=True)

    def add_player(self, p_class, player):
        active = p_class(player, self)
        self.__players.append(active)

    def sub(self, subbed, new_player):
        i = 0
        while self.__players[i] is not subbed:
            i += 1
        active = type(subbed)(new_player, self)
        if subbed.is_captain:
            active.is_turn = subbed.is_turn
        self.__players[i] = active

    def swap_player(self, p_out, p_in):
        i = 0
        while self.__players[i] is not p_out:
            i += 1
        self.__players[i] = p_in
