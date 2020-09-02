import modules.config as cfg
from modules.exceptions import ElementNotFound
from modules.enumerations import PlayerStatus

from discord import Status

_rolesDict = dict()
_guild = None


def getRole(key):
    role = _rolesDict.get(key)
    if role is None:
        raise ElementNotFound(key)
    return role


def init(client):
    global _guild
    _guild = client.get_channel(cfg.discord_ids["rules"]).guild
    _rolesDict["registered"] = _guild.get_role(
        cfg.discord_ids["registered_role"])
    _rolesDict["notify"] = _guild.get_role(cfg.discord_ids["notify_role"])
    _rolesDict["info"] = _guild.get_role(cfg.discord_ids["info_role"])


async def checkRoles(players):
    global _guild
    for p in players:
        memb = _guild.get_member(p.id)
        if memb is not None:
            await onNotifyUpdate(p)
            await memb.remove_roles(_rolesDict["info"])


async def onNotifyUpdate(player):
    global _guild
    memb = _guild.get_member(player.id)
    if player.status is PlayerStatus.IS_REGISTERED and player.isNotify and memb.status not in (Status.offline, Status.dnd):
        if _rolesDict["notify"] not in memb.roles:
            await memb.add_roles(_rolesDict["notify"])
        if _rolesDict["registered"] in memb.roles:
            await memb.remove_roles(_rolesDict["registered"])
    else:
        if _rolesDict["registered"] not in memb.roles:
            await memb.add_roles(_rolesDict["registered"])
        if _rolesDict["notify"] in memb.roles:
            await memb.remove_roles(_rolesDict["notify"])
