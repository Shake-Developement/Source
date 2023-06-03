############
#
from importlib import reload
from typing import Literal, Optional

from discord import Object, PartialEmoji
from discord.ext.commands import Cog, Greedy, command, guild_only, is_owner

from Classes import ShakeBot, ShakeContext, Testing, _, extras, locale_doc, setlocale

from . import sync, testing


########
#
class sync_extension(Cog):
    def __init__(self, bot) -> None:
        self.bot: ShakeBot = bot
        try:
            reload(sync)
        except:
            pass

    @property
    def display_emoji(self) -> PartialEmoji:
        return PartialEmoji(name="\N{SATELLITE ANTENNA}")

    def category(self) -> str:
        return "moderation"

    @command(name="sync")
    @extras(owner=True)
    @guild_only()
    @is_owner()
    @setlocale()
    @locale_doc
    async def sync(
        self,
        ctx: ShakeContext,
        guilds: Greedy[Object] = None,
        spec: Optional[Literal["~", "*", "^"]] = None,
        dump: Optional[bool] = False,
    ):
        _(
            """synchronize the bot with its commands

            The synchronization is used to reload the changes.
            Synchronize when ...
            - ...commands, arguments or permissions have been added, removed or changed
            - ...a global/server command becomes a server/global command

            Parameters
            -----------
            guilds: Optional[strl]
                the guilds

            spec: Optional[Literal["~", "*", "^"]]
                the spec

            dump: Optional[bool]
                if dump"""
        )

        if ctx.testing:
            try:
                reload(testing)
            except Exception as e:
                await self.bot.testing_error(module=testing, error=e)
                ctx.testing = False
        do = testing if ctx.testing else sync

        try:
            await do.command(ctx=ctx, guilds=guilds, spec=spec, dump=dump).__await__()

        except:
            if ctx.testing:
                raise Testing
            raise


async def setup(bot):
    await bot.add_cog(sync_extension(bot))


#
############
