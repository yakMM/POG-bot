# This file is an example of test script for an easier development

from modules.lobby import add_to_lobby
from classes.players import get_player
import asyncio
from discord.ext import commands
from logging import getLogger

log = getLogger("pog_bot")


def get_ids():
    # Enter here a list of discord IDS of accounts you wish to use for the testing
    # For example:
    # return [0000, 0000, 0000, 0000]
    from test2 import id3s
    return id3s


def test_hand(client):
    ids = get_ids()

    @client.command()
    @commands.guild_only()
    async def x(ctx, *args):
        if len(args) == 0:
            await launch(ctx, ids, 0)
        else:
            await launch(ctx, ids, int(args[0]))


async def launch(ctx, id_list, tier):

    players = [get_player(id) for id in id_list]

    for p in players:
        add_to_lobby(p)

    if tier == 1:
        return

    await asyncio.sleep(2)

    match = players[0].match
    teams = match.teams
    cap1, cap2 = None, None

    for tm in teams:
        if tm.captain.is_turn:
            cap1 = tm.captain
        else:
            cap2 = tm.captain

    match.demote(cap1)

    if tier == 2:
        return

    await asyncio.sleep(3)
    await match.pick(ctx, cap2, ["VS"])
    await asyncio.sleep(1)
    await match.pick(ctx, cap1, ["TR"])

    if tier == 3:
        return

    await asyncio.sleep(3)
    await match.base_selector.select_by_index(ctx, cap1, 0)

