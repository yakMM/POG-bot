from general.enumerations import MatchStatus
from modules.reactions import ReactionHandler

from display import AllStrings as disp, ContextWrapper

import discord.errors

import match_process.meta as meta
import match_process.common_picking as common
from asyncio import sleep

import modules.accounts_handler as accounts
import modules.database as db
import modules.config as cfg

class GettingReady(meta.Process, status=MatchStatus.IS_WAITING):

    def __init__(self, match):
        self.match = match

        self.match.teams[1].captain.is_turn = True
        self.match.teams[0].captain.is_turn = True

        super().__init__(match)

    @meta.init_loop
    async def init(self):
        await disp.ACC_SENDING.send(self.match.channel)

        for tm in self.match.teams:
            for a_player in tm.players:
                if not a_player.has_own_account:
                    success = await accounts.give_account(a_player)
                    if success:
                        self.match.players_with_account.append(a_player)
                    else:
                        await disp.ACC_NOT_ENOUGH.send(self.match.channel)
                        await self.clear()
                        return

        # Try to send the accounts:
        for a_player in self.match.players_with_account:
            await accounts.send_account(self.match.channel, a_player)

        await disp.ACC_SENT.send(self.match.channel)

    @meta.public
    async def clear(self, ctx):
        await self.match.clean()
        await disp.MATCH_CLEARED.send(ctx)

    @meta.public
    async def remove_account(self, a_player):
        await accounts.terminate_account(a_player)
        self.match.players_with_account.remove(a_player)

    @meta.public
    async def give_account(self, a_player):
        success = await accounts.give_account(a_player)
        if success:
            self.match.players_with_account.append(a_player)
            await accounts.send_account(self.match.channel, a_player)
            await disp.ACC_GIVING.send(self.match.channel, a_player.mention)
        else:
            await disp.ACC_NOT_ENOUGH.send(self.match.channel)
            await self.clear()

    @meta.public
    async def sub(self, ctx, subbed):
        new_player = await common.after_pick_sub(ctx, self.match, subbed, clean_subbed=False)
        if not new_player:
            return
        if not subbed.active.has_own_account:
            await self.remove_account(subbed.active)
            subbed.on_player_clean()
        if not new_player.active.has_own_account:
            await self.give_account(new_player.active)


    @meta.public
    async def pick_status(self, ctx):
        await disp.PK_FACTION_INFO.send(ctx)

    @meta.public
    async def pick(self, ctx, captain, args):
        await common.faction_change(ctx, captain, args, self.match)
