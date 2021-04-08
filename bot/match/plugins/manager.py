from .logger import SimpleLogger
from .ts3_interface import AudioBot

_plugins = [SimpleLogger, AudioBot]


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
            getattr(p, event)(*args, **kwargs)

    def __getattr__(self, item):
        return VirtualAttribute(self, item)


