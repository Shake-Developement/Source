from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, Tuple

from discord import Guild, Member, Message, TextChannel
from discord.ext.commands import BucketType, CooldownMapping

from Classes import (
    MISSING,
    CountingBatch,
    ShakeBot,
    ShakeEmbed,
    TextFormat,
    _,
    cleanup,
    current,
    evaluate,
    string_is_calculation,
)

Literals = Literal["AboveMe", "Counting", "OneWord"]
SystemType = Tuple[Optional[ShakeEmbed], bool, bool]
############
#


class Event:
    bot: ShakeBot
    guild: Guild
    channel: TextChannel
    message: Message
    spam_control: CooldownMapping

    def __init__(self, message: Message, bot: ShakeBot):
        self.bot = bot
        self.author = message.author
        self.guild = message.guild
        self.channel = message.channel
        self.content = message.content
        self.message = message
        self.game = "Counting"

    async def __await__(self):
        ctx = await self.bot.get_context(self.message)

        if ctx and ctx.valid and ctx.command:
            return

        if isinstance(self.channel, TextChannel):
            await self.check()
        return

    async def check(self):
        cache = self.bot.cache.get(self.game, list())

        if self.channel.id in cache:
            done = cache.get(self.channel.id, {}).get("done", None)
            if done:
                return
            await self.counting()
        else:
            async with self.bot.gpool.acquire() as connection:
                records: Dict[int, bool] = dict(
                    await connection.fetch(
                        f"SELECT channel_id, done FROM {self.game.lower()} WHERE guild_id = $1",
                        self.guild.id,
                    )
                )
            if self.channel.id in records:
                if done := records[self.channel.id]:
                    return

                if (not self.message.content) or bool(self.message.attachments):
                    embed = ShakeEmbed(timestamp=None)
                    embed.description = TextFormat.bold(
                        _(
                            "You should not write anything other than messages with text content!"
                        )
                    )
                    await self.message.reply(embed=embed, delete_after=10)
                    await self.message.delete(delay=10)
                else:
                    await self.counting()

        await self.unvalidate()
        return True

    async def unvalidate(self) -> None:
        async with self.bot.gpool.acquire() as connection:
            unvalids = [
                str(r[0])
                for r in await connection.fetch(
                    f"SELECT channel_id FROM {self.game} WHERE guild_id = $1",
                    self.guild.id,
                )
                if not self.bot.get_channel(r[0])
            ]

            if unvalids:
                await connection.execute(
                    f"DELETE FROM {self.game} WHERE channel_id IN {'('+', '.join(unvalids)+')'};",
                )

    async def counting(self):
        system = Counting(
            bot=self.bot,
            channel=self.channel,
            guild=self.guild,
            spam_control=CooldownMapping.from_cooldown(10, 12.0, BucketType.user),
        )
        embed, delete, bad_reaction = await system.__await__(
            member=self.author, message=self.message
        )

        if all([_ is None for _ in (embed, delete, bad_reaction)]):
            return

        if not bad_reaction is MISSING:
            try:
                await self.message.add_reaction(
                    ("☑️", self.bot.emojis.cross, "⚠️")[bad_reaction]
                )
            except:
                pass
        if embed:
            last = self.channel.last_message
            if last:
                descriptions = [embed.description[-22:] for embed in last.embeds]
            else:
                descriptions = []
            if not embed.description[-22:] in descriptions:
                try:
                    await self.message.reply(
                        embed=embed, delete_after=10 if delete else None
                    )
                except:
                    await self.message.channel.send(
                        embed=embed, delete_after=10 if delete else None
                    )
        if delete:
            await self.message.delete(delay=10)
        return True


class Counting:
    channel: TextChannel
    guild: Guild
    cache: Dict[int, List]
    spam_control: CooldownMapping

    def __init__(
        self,
        bot: ShakeBot,
        guild: Guild,
        channel: TextChannel,
        spam_control: CooldownMapping,
    ):
        self.bot = bot
        self.cache = self.bot.cache["Counting"]
        self.channel = channel
        self.guild = guild
        self.spam_control = spam_control
        self._auto_spam_count = Counter()

    async def __await__(
        self, member: Member, message: Message
    ) -> Tuple[ShakeEmbed, bool, Literal[1, 2, 3]]:
        content: str = cleanup(message.clean_content.strip())
        time = message.created_at
        testing: bool = any(
            _.id in set(self.bot.testing) for _ in [self.channel, self.guild, member]
        )

        if self.channel.id in self.cache:
            record: dict = self.cache[self.channel.id]
        else:
            async with self.bot.gpool.acquire() as connection:
                record: dict = await connection.fetchrow(
                    "SELECT * FROM counting WHERE channel_id = $1",
                    self.channel.id,
                )

        streak: int = record.get("streak", 0) or 0
        best: int = record.get("best", 0) or 0
        user_id: int = record.get("user_id")
        message_id: int = record.get("message_id")
        goal: int = record.get("goal")
        count: int = record.get("count", 0) or 0
        start: int = record.get("start", 0) or 0
        used: datetime = record.get("used")
        done: bool = record.get("done", False)
        webhook: bool = record.get("webhook", None) or None
        direction: bool = record.get("direction", True)
        react: bool = record.get("react", True)
        numbers: bool = record.get("numbers")
        math: bool = record.get("math", False)
        restart = reached = False

        current.set(await self.bot.i18n.get_guild(self.guild.id, default="en-US"))

        embed = ShakeEmbed(timestamp=None)
        delete = passed = False
        bad_reaction = 0

        influence = +1 if direction is True else -1

        if not await self.syntax_check(content, math):
            if numbers:
                embed.description = TextFormat.bold(
                    _("You can't use anything but arithmetic here.")
                )
                delete = True
                bad_reaction = 1
            else:
                return None, None, None

        elif not await self.member_check(
            testing=testing, user_id=user_id, member=member
        ):
            embed.description = TextFormat.bold(
                _("You are not allowed to count multiple numbers in a row.")
            )
            bad_reaction = 1
            delete = True

        elif not await self.check_number(content, count, direction, math):
            bucket = self.spam_control.get_bucket(message)
            retry_after = bucket and bucket.update_rate_limit(time.timestamp())
            if retry_after:  # member.id != self.owner_id:
                self._auto_spam_count[member.id] += 1

            if self._auto_spam_count[member.id] >= 5:
                embed.description = TextFormat.bold(
                    _("You failed to often. No stats have been changed!!")
                )
                del self._auto_spam_count[member.id]
                bad_reaction = 2
            else:
                self._auto_spam_count.pop(member.id, None)
                if streak != 0:
                    s = _("The streak of {streak} was broken!")
                    if streak > best:
                        s = _("You've topped your best streak with {streak} numbers 🔥")
                    s = s.format(streak=TextFormat.codeblock(f" {streak} "))
                else:
                    s = ""

                if count == start:
                    embed.description = TextFormat.bold(
                        _(
                            "Incorrect number! The next number remains {start}. {streak}"
                        ).format(
                            start=TextFormat.codeblock(f" {start + influence} "),
                            streak=s,
                        )
                    )
                    bad_reaction = 2
                else:
                    embed.description = TextFormat.bold(
                        _(
                            "{user} ruined it at {count}. The next number is {start}. {streak}"
                        ).format(
                            user=member.mention,
                            count=TextFormat.underline(count + influence),
                            streak=s,
                            start=TextFormat.codeblock(f" {start + influence} "),
                        )
                    )
                    bad_reaction = 1
                    user_id = None
                restart = True
                streak = 0

        else:
            passed = True

            if goal and count + 1 >= goal:
                reached = True
                embed.description = TextFormat.bold(
                    _(
                        "You've reached your goal of {goal} {emoji} Congratulations!"
                    ).format(goal=goal, emoji="<a:tadaa:1038228851173625876>")
                )
            elif direction is False and count - 1 <= 0:
                embed.description = TextFormat.bold(
                    _(
                        "You've reached the end of the numbers until 0 {emoji} Congratulations!"
                    ).format(emoji="<a:tadaa:1038228851173625876>")
                )
                done = True
            else:
                embed = None

        new = start if restart else (count + influence) if passed else count

        await self.counting(
            channel=self.channel,
            guild=self.guild,
            user=member,
            direction=direction,
            used=time,
            count=count,
            failed=not passed,
        )

        s = streak + 1 if passed else streak
        self.cache[self.channel.id]: CountingBatch = {
            "used": str(
                time.replace(tzinfo=timezone.utc).isoformat() if passed else used
            ),
            "channel_id": self.channel.id,
            "user_id": member.id if passed else user_id,
            "message_id": message.id if passed else message_id,
            "best": s if s > best else best,
            "count": new,
            "done": done,
            "goal": None if reached else goal,
            "webhook": webhook,
            "streak": s,
            "start": start,
            "direction": direction,
            "react": react,
            "numbers": numbers,
            "math": math,
        }
        return embed, delete, bad_reaction if react == True else MISSING

    async def counting(
        self,
        channel: TextChannel,
        guild: Guild,
        user: Member,
        direction: bool,
        used: datetime,
        count: Optional[int],
        failed: bool,
    ) -> None:
        self.bot.cache["Countings"].append(
            {
                "guild_id": guild.id,
                "channel_id": channel.id,
                "user_id": user.id,
                "direction": direction,
                "used": str(used.replace(tzinfo=timezone.utc).isoformat()),
                "count": count,
                "failed": failed,
            }
        )

    async def syntax_check(self, content: str, math: bool):
        if not content.isdigit():
            if math and string_is_calculation(content):
                return True
            return False
        return True

    async def check_number(self, content: str, count: int, direction: bool, math: bool):
        if math:
            number = evaluate(content)
        else:
            number = int(content)

        if direction is True and not number == count + 1:
            return False

        if direction is False and not number == count - 1:
            return False

        return True

    async def member_check(self, testing: bool, user_id: int, member: Member):
        if testing:
            return True
        elif user_id == member.id:
            return False
        return True


#
############