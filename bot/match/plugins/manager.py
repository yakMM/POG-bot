from .logger import SimpleLogger
from .ts3_interface import AudioBot
from .plugin import PluginDisabled
from logging import getLogger
import modules.config as cfg

_plugins = [SimpleLogger, AudioBot]

log = getLogger("pog_bot")


class VirtualAttribute:
    def __init__(self, manager, name):
        self.manager = manager
        self.name = name

    def __call__(self, *args, **kwargs):
        self.manager.on_event(self.name, *args, **kwargs)


class PluginManager:
    def __init__(self, match):
        plugins_enabled = cfg.LAUNCH_STR != "_test"
        self.match = match
        self.plugins = list()
        if plugins_enabled:
            for Plug in _plugins:
                try:
                    self.plugins.append(Plug(self.match))
                except PluginDisabled as e:
                    log.warning(f"Could not start plugin '{Plug.__name__}'\n{e}")

    def on_event(self, event, *args, **kwargs):
        for p in self.plugins:
            try:
                getattr(p, event)(*args, **kwargs)
            except Exception as e:
                log.error(f"Error occurred in plugin {type(p).__name__}\n{e}")

    async def async_clean(self):
        for p in self.plugins:
            try:
                await p.async_clean()
            except Exception as e:
                log.error(f"Error occurred when clearing plugin {type(p).__name__}\n{e}")

    def __getattr__(self, item):
        return VirtualAttribute(self, item)


