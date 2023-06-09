############
#
from importlib import reload
from typing import Any

from discord import PartialEmoji
from discord.app_commands import guild_only
from discord.ext.commands import command, is_owner

from Classes import ShakeBot, ShakeContext, Testing, _, locale_doc, setlocale
from Classes.checks import extras

from ..other import Other
from . import repl, testing


########
#
class repl_extension(Other):
    def __init__(self, bot: ShakeBot):
        super().__init__(bot=bot)
        self.last: Any = None
        self.env = dict()
        try:
            reload(repl)
        except:
            pass

    @property
    def display_emoji(self) -> PartialEmoji:
        return PartialEmoji(name="\N{WASTEBASKET}")

    @command(name="repl")
    @extras(owner=True)
    @guild_only()
    @is_owner()
    @setlocale()
    @locale_doc
    async def repl(self, ctx: ShakeContext, *, code: str) -> None:
        _(
            """Run your own xyz codes.
            
            You can simply specify this code as an argument and also in quotes (`).
            Optionally you can use common attributes like ctx, bot etc. in the code.
            
            Environment Variables:
                ctx     - command invocation context
                bot     - bot object
                channel - the current channel object
                author  - command author's member object
                message - the command's message object
                _       - The result of the last dev command.
            
            Parameters
            -----------
            code: str
                the code"""
        )

        if ctx.testing:
            try:
                reload(testing)
            except Exception as e:
                await self.bot.testing_error(module=testing, error=e)
                ctx.testing = False
        do = testing if ctx.testing else repl
        try:
            last = await do.command(
                ctx=ctx, code=code, env=self.env, last=self.last
            ).__await__()

            if last:
                self.last = last

        except:
            if ctx.testing:
                raise Testing
            raise


async def setup(bot: ShakeBot):
    await bot.add_cog(repl_extension(bot))


#
############