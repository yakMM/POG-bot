import signal
import sys
import asyncio
from display import AllStrings as disp, ContextWrapper
import modules.config as cfg
import modules.lobby as lobby
import modules.database as db


def save_state():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(disp.STOP.send(ContextWrapper.channel(cfg.channels["spam"])))
    lb = lobby.get_all_ids_in_lobby()
    db.set_field("restart_data", 0, {"last_lobby": lb})
    sys.exit(0)


def init():
    signal.signal(signal.SIGINT, save_state)
