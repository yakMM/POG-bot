# @CHECK 2.0 features OK

import modules.config as cfg
from modules.exceptions import ElementNotFound
from modules.enumerations import PlayerStatus

from discord import Status
from discord import PermissionOverwrite

_roles_dict = dict()
_guild = None


def init(client):
    global _guild
    _guild = client.get_channel(cfg.channels["rules"]).guild
    _roles_dict["registered"] = _guild.get_role(cfg.roles["registered"])
    _roles_dict["notify"] = _guild.get_role(cfg.roles["notify"])
    _roles_dict["info"] = _guild.get_role(cfg.roles["info"])
    _roles_dict["admin"] = _guild.get_role(cfg.roles["admin"])


def is_admin(member):
    """ Check if user is admin
    """
    if member is None:
        return False
    return _roles_dict["admin"] in member.roles


async def force_info(p_id):
    global _guild
    memb = _guild.get_member(p_id)
    if memb is None:
        return
    if _roles_dict["info"] not in memb.roles:
        await memb.add_roles(_roles_dict["info"])
    if _roles_dict["registered"] in memb.roles:
        await memb.remove_roles(_roles_dict["registered"])
    if _roles_dict["notify"] in memb.roles:
        await memb.remove_roles(_roles_dict["notify"])


async def role_update(player):
    if player.is_timeout:
        await force_info(player.id)
        return
    await perms_muted(False, player.id)
    global _guild
    memb = _guild.get_member(player.id)
    if memb is None:
        return
    if player.status is PlayerStatus.IS_REGISTERED and player.is_notify and memb.status not in (Status.offline, Status.dnd):
        if _roles_dict["notify"] not in memb.roles:
            await memb.add_roles(_roles_dict["notify"])
        if _roles_dict["registered"] in memb.roles:
            await memb.remove_roles(_roles_dict["registered"])
    else:
        if _roles_dict["registered"] not in memb.roles:
            await memb.add_roles(_roles_dict["registered"])
        if _roles_dict["notify"] in memb.roles:
            await memb.remove_roles(_roles_dict["notify"])
    if _roles_dict["info"] in memb.roles:
        await memb.remove_roles(_roles_dict["info"])


async def perms_muted(value, p_id):
    global _guild
    memb = _guild.get_member(p_id)
    if memb is None:
        return
    channel = _guild.get_channel(cfg.channels["muted"])
    if value:
        over = _guild.get_channel(cfg.channels["lobby"]).overwrites_for(_roles_dict["registered"])
        if memb not in channel.overwrites:
            await channel.set_permissions(memb, overwrite=over)
    else:
        if memb in channel.overwrites:
            await channel.set_permissions(memb, overwrite=None)


async def channel_freeze(value, id):
    global _guild
    channel = _guild.get_channel(id)
    ov_notify = channel.overwrites_for(_roles_dict["notify"])
    ov_registered = channel.overwrites_for(_roles_dict["registered"])
    ov_notify.send_messages = not value
    ov_registered.send_messages = not value
    await channel.set_permissions(_roles_dict["notify"], overwrite=ov_notify)
    await channel.set_permissions(_roles_dict["registered"], overwrite=ov_registered)
