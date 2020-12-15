from display import send
from lib.tasks import loop

from modules.enumerations import MatchStatus
from random import choice as random_choice

from classes.teams import Team
from classes.players import TeamCaptain, ActivePlayer


class PlayerPicking:

    def __init__(self, match, objects, data, p_list):
        self.players = dict()
        self.objects = objects
        self.data = data
        self.match = match

        for p in p_list:
            self.players[p.id] = p
            p.on_match_selected(match)

        self._init.start()


    def __find_captains(self):
        """ Pick at random two captains
            TODO: Base this pick on some kind of stats or a role
        """
        for i in range(2):
            key = random_choice(list(self.players))
            self.objects.teams[i].add_player(TeamCaptain, self.players.pop(key))


    @loop(count=1)
    async def _init(self):
        """ Init the match channel, ping players, find two captains \
            and ask them to start picking players
        """
        # Inform players of match init
        players_ping = " ".join(p.mention for p in self.players.values())
        self.objects.audio_bot.drop_match()
        await send("MATCH_INIT", self.objects.channel, players_ping)

        # Initialize teams
        self.objects.teams[0] = Team(0, f"Team 1", self.match)
        self.objects.teams[0] = Team(1, f"Team 2", self.match)

        # Find two captains, first one will pick first
        self.__find_captains()
        self.objects.teams[0].captain.is_turn = True

        # Ready for players to pick
        self.objects.status = MatchStatus.IS_PICKING
        self.objects.audio_bot.select_teams()
        await send("MATCH_SHOW_PICKS", self.objects.channel,\
            self.objects.teams[0].captain.mention, match=self.match)

    