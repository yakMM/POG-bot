# @CHECK 2.0 features OK

import modules.config as cfg

from discord import Status

_roles_dict = dict()
_guild = None


def init(client):
    global _guild
    _guild = client.get_channel(cfg.channels["rules"]).guild
    for role in cfg.roles.keys():
        _roles_dict[role] = _guild.get_role(cfg.roles[role])


def is_admin(member):
    """ Check if user is admin
    """
    if member is None:
        return False
    return _roles_dict["admin"] in member.roles


def is_muted(member):
    if member is None:
        return False
    return _roles_dict["muted"] in member.roles


async def remove_roles(p_id):
    memb = _guild.get_member(p_id)
    if memb is None:
        return
    if _roles_dict["registered"] in memb.roles:
        await memb.remove_roles(_roles_dict["registered"])
    if _roles_dict["notify"] in memb.roles:
        await memb.remove_roles(_roles_dict["notify"])


async def role_update(player):
    if player.is_timeout:
        await remove_roles(player.id)
        return
    if player.is_away:
        await remove_roles(player.id)
        return
    await perms_muted(False, player.id)
    memb = _guild.get_member(player.id)
    if memb is None:
        return
    if player.is_notify and memb.status not in (Status.offline, Status.dnd) and not (player.is_lobbied or player.match):
        if _roles_dict["notify"] not in memb.roles:
            await memb.add_roles(_roles_dict["notify"])
        if _roles_dict["registered"] in memb.roles:
            await memb.remove_roles(_roles_dict["registered"])
    else:
        if _roles_dict["registered"] not in memb.roles:
            await memb.add_roles(_roles_dict["registered"])
        if _roles_dict["notify"] in memb.roles:
            await memb.remove_roles(_roles_dict["notify"])


async def perms_muted(value, p_id):
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


async def modify_match_channel(channel, view):
    ov_notify = channel.overwrites_for(_roles_dict["notify"])
    ov_registered = channel.overwrites_for(_roles_dict["registered"])
    ov_notify.view_channel = view
    ov_notify.send_messages = view
    ov_registered.view_channel = view
    ov_registered.send_messages = view
    await channel.set_permissions(_roles_dict["notify"], overwrite=ov_notify)
    await channel.set_permissions(_roles_dict["registered"], overwrite=ov_registered)
    # await channel.edit(name=f"pog-match-{match.id}")


async def channel_freeze(value, id):
    channel = _guild.get_channel(id)
    ov_notify = channel.overwrites_for(_roles_dict["notify"])
    ov_registered = channel.overwrites_for(_roles_dict["registered"])
    ov_notify.send_messages = not value
    ov_registered.send_messages = not value
    await channel.set_permissions(_roles_dict["notify"], overwrite=ov_notify)
    await channel.set_permissions(_roles_dict["registered"], overwrite=ov_registered)
