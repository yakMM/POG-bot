import signal
import os
import sys

import modules.lobby as lobby
import modules.database as db
from logging import getLogger
import asyncio

log = getLogger("pog_bot")


def save_state(loop):
    log.info("SIGINT caught, saving state...")
    lb = lobby.get_all_ids_in_lobby()
    db.set_field("restart_data", 0, {"last_lobby": lb})
    log.info("Stopping...")
    loop.stop()
    sys.exit(0)


def init():
    # signal.signal(signal.SIGINT, save_state)
    try:
        loop = asyncio.get_event_loop()
        asyncio.get_event_loop().add_signal_handler(signal.SIGINT, lambda: save_state(loop))
    except NotImplementedError:
        pass
