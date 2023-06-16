from typing import Optional

from discord import Forbidden, HTTPException, PartialEmoji, TextChannel

from Classes import ShakeCommand, ShakeEmbed, Slash, TextFormat, _

############
#


class command(ShakeCommand):
    async def setup(
        self,
        channel: Optional[TextChannel],
        goal: Optional[int],
        numbers: bool,
        react: bool,
    ):
        if not channel:
            try:
                channel = await self.ctx.guild.create_text_channel(
                    name="counting", slowmode_delay=5
                )
            except (
                HTTPException,
                Forbidden,
            ):
                await self.ctx.chat(
                    _(
                        "The Counting-Game couldn't setup because I have no permissions to do so."
                    )
                )
                return False

        async with self.ctx.db.acquire() as connection:
            query = "SELECT * FROM counting WHERE channel_id = $1"
            record = await connection.fetchrow(query, channel.id)
            if record:
                await self.ctx.chat(
                    _(
                        "The Counting-Game couldn't setup because there is alredy one in {channel}."
                    ).format(channel=channel.mention)
                )
                return False

            query = "INSERT INTO counting (channel_id, guild_id, goal, hardcore, numbers, react) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT DO NOTHING"
            await connection.execute(
                query, channel.id, self.ctx.guild.id, goal, False, numbers, react
            )

        await self.ctx.chat(
            _("The Counting-Game is succsessfully setup in {channel}").format(
                channel=channel.mention
            )
        )

    async def info(self) -> None:
        slash = await Slash(self.ctx.bot).__await__(
            self.ctx.bot.get_command("counting")
        )

        setup = self.ctx.bot.get_command("counting setup")
        cmd, setup = await slash.get_sub_command(setup)

        counting = self.ctx.bot.get_command("counting configure")
        cmd, configure = await slash.get_sub_command(counting)

        embed = ShakeEmbed()
        embed.title = TextFormat.blockquotes(_("Welcome to „Counting“"))
        embed.description = (
            TextFormat.italics(
                _("Thanks for your interest in the game in this awesome place!")
            )
            + " "
            + str(PartialEmoji(name="wumpus", id=1114674858706616422))
        )
        embed.add_field(
            name=_("How to setup the game?"),
            value=_(
                "Get started by using the command {command} to create and setup the essential channel"
            ).format(command=setup),
            inline=False,
        )
        embed.add_field(
            name=_("How to use the game?"),
            value=_(
                "This game is all about numbers, which are posted one after the other in order by different users in the chat\n"
            ),
            inline=False,
        )
        rules = [
            _("One person can't count numbers in a row (others are required)."),
            _("No botting, if you have fail to often, you'll get muted."),
            _("If you break count, the count will reset to a calculated checkpoint."),
        ]
        embed.add_field(
            name=_("Counting rules"),
            value="\n".join(TextFormat.list(_) for _ in rules),
            inline=False,
        )
        embed.add_field(
            name=_("How to configure the game?"),
            value=_(
                "Customize all kind of properties for „Counting“ by using the the command {command}!"
            ).format(command=configure),
            inline=False,
        )
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/946862628179939338/1060213944981143692/banner.png"
        )
        await self.ctx.send(embed=embed, ephemeral=True)

    async def configure(
        self, channel: TextChannel, count: Optional[int], react: Optional[bool]
    ):
        async with self.ctx.db.acquire() as connection:
            query = "SELECT * FROM counting WHERE channel_id = $1"
            record = await connection.fetchrow(query, channel.id)
            if not record:
                await self.ctx.chat(
                    _(
                        "There is no Counting-Game in the given channel {channel} that we could configure."
                    ).format(channel=channel.mention)
                )
                return False

            count = (count - 1) if count else record["count"]
            react = react if not react is None else record["react"]
            query = "UPDATE counting SET count = $2, react = $3 WHERE channel_id = $1"
            await connection.execute(query, channel.id, count, react)

        if count is not None:
            await channel.send(
                _("The next number in here has been set to {count}").format(count=count)
            )

        return await self.ctx.chat(
            _(
                "The stats of the Counting-Game in {channel} has been succsessfully configured."
            ).format(channel=channel.mention)
        )


#
############
