


class PlayerPicking:

    def __init__(self, match, p_list):
        self.__players = dict()
        self.__match = match

        for p in p_list:
            self.__players[p.id] = p
            p.on_match_selected(match)

        self._spin_up.start()


    @loop(count=1)
    async def _spin_up(self):
        self.__audio_bot.drop_match()
        await send("MATCH_INIT", self.__channel, " ".join(self.player_pings))
        self.__accounts = AccountHander(self)
        self.__map_selector = MapSelection(self, main_maps_pool)
        for i in range(len(self.__teams)):
            self.__teams[i] = Team(i, f"Team {i + 1}", self)
            key = random_choice(list(self.__players))
            self.__teams[i].add_player(TeamCaptain, self.__players.pop(key))
        self.__teams[0].captain.is_turn = True
        self.__status = MatchStatus.IS_PICKING
        self.__audio_bot.select_teams()
        await send("MATCH_SHOW_PICKS", self.__channel, self.__teams[0].captain.mention, match=self)