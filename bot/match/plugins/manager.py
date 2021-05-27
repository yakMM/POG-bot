from .logger import SimpleLogger
from .ts3_interface import AudioBot
from .squittal_interface import SquittalInterface
from logging import getLogger

_plugins = [SimpleLogger, AudioBot, SquittalInterface]

log = getLogger("pog_bot")


class VirtualAttribute:
    def __init__(self, manager, name):
        self.manager = manager
        self.name = name

    def __call__(self, *args, **kwargs):
        self.manager.on_event(self.name, *args, **kwargs)


class PluginManager:
    def __init__(self, match):
        self.match = match
        self.plugins = list()
        for Plug in _plugins:
            self.plugins.append(Plug(self.match))

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


