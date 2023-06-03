############
#
from importlib import reload
from typing import Optional

from discord import PartialEmoji
from discord.ext.commands import command, guild_only, is_owner

from Classes import ShakeBot, ShakeContext, Testing, _, extras, locale_doc, setlocale

from ..other import Other
from . import leave, testing


########
#
class leave_extension(Other):
    def __init__(self, bot: ShakeBot) -> None:
        super().__init__(bot=bot)
        try:
            reload(leave)
        except:
            pass

    @property
    def display_emoji(self) -> PartialEmoji:
        return PartialEmoji(name="blobleave", animated=True, id=1058033660755972219)

    def category(self) -> str:
        return "other"

    @command(name="leave")
    @extras(owner=True)
    @guild_only()
    @is_owner()
    @setlocale()
    @locale_doc
    async def leave(self, ctx: ShakeContext, *, guild: Optional[int] = None):
        _(
            """Leave a guild

            Parameters
            -----------
            guild: int
                the ID of the server"""
        )

        if ctx.testing:
            try:
                reload(testing)
            except Exception as e:
                self.bot.log.critical(
                    "Could not load {name}, will fallback ({type})".format(
                        name=testing.__file__, type=e.__class__.__name__
                    )
                )
                ctx.testing = False
        do = testing if ctx.testing else leave

        try:
            await do.command(ctx=ctx, guild=guild).__await__()

        except:
            if ctx.testing:
                raise Testing
            raise


async def setup(bot: ShakeBot):
    await bot.add_cog(leave_extension(bot))


#
############
