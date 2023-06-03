from asyncio import TaskGroup
from typing import List, Literal

from asyncpg import Record
from discord import Guild, Member, Message, TextChannel

from Classes import MISSING, ShakeBot, aboveme, counting

############
#


class Event:
    def __init__(self, message: Message, bot: ShakeBot):
        self.bot: ShakeBot = bot
        self.author: Member = message.author
        self.guild: Guild = message.guild
        self.channel: TextChannel = message.channel
        self.message: Message = message

    async def __await__(self):
        ctx = await self.bot.get_context(self.message)
        if ctx.valid and ctx.command:
            return

        async with TaskGroup() as tg:
            tg.create_task(self.check(game="counting"))
            tg.create_task(self.check(game="aboveme"))
        return

    async def check(self, game: Literal["aboveme", "counting"]):
        cache = self.bot.cache.get(game, list())
        r = False
        if self.channel.id in cache:
            func = getattr(self, game, MISSING)
            if func:
                r = await func()
            else:
                return False
        else:
            async with self.bot.gpool.acquire() as connection:
                records: List[int] = [
                    r[0]
                    for r in await connection.fetch(
                        f"SELECT channel_id FROM {game} WHERE guild_id = $1",
                        self.guild.id,
                    )
                ]
            if self.channel.id in records:
                self.bot.cache.setdefault(game, list())
                self.bot.cache[game].append(self.channel.id)
                func = getattr(self, game, MISSING)
                if func:
                    r = await func()

        await self.unvalidate(game=game)
        return r

    async def unvalidate(self, game: Literal["aboveme", "counting"]) -> None:
        async with self.bot.gpool.acquire() as connection:
            records = [
                r[0]
                for r in await connection.fetch(
                    f"SELECT channel_id FROM {game} WHERE guild_id = $1",
                    self.guild.id,
                )
            ]

            unvalids = [
                str(channel_id)
                for channel_id in records
                if not self.bot.get_channel(channel_id)
            ]
            if unvalids:
                await connection.execute(
                    f"DELETE FROM {game} WHERE channel_id IN {'('+', '.join(unvalids)+')'};",
                )

    # async def await_oneword(self):
    #     oneword = systems.oneword(
    #         member=self.author, message=self.message, bot=self.bot
    #     )
    #     if await oneword.__await__() is False:
    #         return False
    #     delete_message = oneword.do.get("delete_message", False)
    #     add_reaction = oneword.do.get("add_reaction", False)
    #     add_bad = oneword.do.get("add_bad_reaction", False)
    #     with suppress(Forbidden, HTTPException):
    #         if add_bad or add_reaction:
    #             await self.message.add_reaction(
    #                 "☑️" if add_reaction else self.bot.emojis.cross
    #             )
    #         if getattr(oneword, "kwargs", None):
    #             await self.message.channel.send(
    #                 **getattr(oneword, "kwargs"),
    #                 delete_after=10 if delete_message else None
    #             )
    #         if delete_message:
    #             await self.message.delete(delay=10)
    #     return True

    async def aboveme(self):
        system = aboveme(
            bot=self.bot,
            member=self.author,
            channel=self.channel,
            guild=self.guild,
            content=self.message.content,
        )
        embed, delete, bad_reaction = await system.__await__()

        if all([embed is None, delete is None, bad_reaction is None]):
            return

        await self.message.add_reaction(("☑️", self.bot.emojis.cross)[bad_reaction])
        if embed:
            await self.channel.send(embed=embed, delete_after=10 if delete else None)
        if delete:
            await self.message.delete(delay=10)
        return True

    async def counting(self):
        system = counting(
            bot=self.bot,
            member=self.author,
            channel=self.channel,
            guild=self.guild,
            content=self.message.content,
        )
        embed, delete, bad_reaction = await system.__await__()

        if all([embed is None, delete is None, bad_reaction is None]):
            return

        await self.message.add_reaction(
            ("☑️", self.bot.emojis.cross, "⚠️")[bad_reaction]
        )
        if embed:
            await self.channel.send(embed=embed, delete_after=10 if delete else None)
        if delete:
            await self.message.delete(delay=10)
        return True


#
############
