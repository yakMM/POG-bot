from classes import Player, PlayerStat
import modules.config as cfg
from display import AllStrings as disp, ContextWrapper
from logging import getLogger

log = getLogger("pog_bot")


async def on_stats(user):
    player = Player.get(user.id)
    if not player:
        await disp.NO_RULE.send(user, "stats", cfg.channels["rules"])
        return
    log.info(f"Stats request from player id: [{player.id}], name: [{player.name}]")
    stat_player = await PlayerStat.get_from_database(player.id, player.name)
    await disp.DISPLAY_STATS.send(user, stats=stat_player)
