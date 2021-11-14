import signal
import asyncio
from display import AllStrings as disp, ContextWrapper
import modules.config as cfg
import modules.lobby as lobby
import modules.database as db
from logging import getLogger

log = getLogger("pog_bot")


async def save_state(sig, frame):
    await disp.STOP.send(ContextWrapper.channel(cfg.channels["spam"]))
    lb = lobby.get_all_ids_in_lobby()
    await db.async_db_call(db.set_field, "restart_data", 0, {"last_lobby": lb})


def init():
    loop = asyncio.get_event_loop()
    try:
        loop.add_signal_handler(signal.SIGINT, save_state)
    except NotImplementedError:
        log.debug("Ignoring exception in 'Signal' module: probably running on windows")
