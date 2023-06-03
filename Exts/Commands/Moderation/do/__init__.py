############
#
from importlib import reload

from discord import PartialEmoji
from discord.ext.commands import guild_only, has_permissions, hybrid_command

from Classes import ShakeBot, ShakeContext, Testing, _, extras, locale_doc, setlocale

from ..moderation import Moderation
from . import do, testing


########
#
class do_extension(Moderation):
    def __init__(self, bot: ShakeBot) -> None:
        super().__init__(bot=bot)
        try:
            reload(do)
        except:
            pass

    @property
    def display_emoji(self) -> PartialEmoji:
        return PartialEmoji(name="\N{PRINTER}")

    def category(self) -> str:
        return "moderation"

    @hybrid_command(name="do")
    @extras(permissions=True)
    @guild_only()
    @has_permissions(administrator=True)
    @setlocale(guild=True)
    @locale_doc
    async def __await__(self, ctx: ShakeContext, times: int, command: str):
        _("""run commands multiple times""")

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
        _do = testing if ctx.testing else do

        try:
            await _do.command(ctx=ctx, times=times, command=command).__await__()

        except:
            if ctx.testing:
                raise Testing
            raise


async def setup(bot: ShakeBot):
    await bot.add_cog(do_extension(bot))


#
############
