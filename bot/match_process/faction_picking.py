
from display import send
from lib.tasks import loop

from modules.enumerations import MatchStatus

class FactionPicking:

    @classmethod
    def get_authorized_attributes(this):
        attr_list = list()
        return attr_list

    def __init__(self, match):
        self.match = match

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = False
        picker = self.match.teams[1].captain

        self.init.start(picker)


    @loop(count=1)
    async def init(self, picker):
        self.match.audio_bot.select_factions()
        await send("PK_OK_FACTION", self.match.channel, picker.mention, match=self.match.proxy)
