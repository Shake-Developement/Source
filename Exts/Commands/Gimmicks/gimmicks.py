from discord import PartialEmoji
from discord.ext import commands

from Classes import ShakeBot, _

############
#


class Gimmicks(commands.Cog):
    def __init__(self, bot: ShakeBot) -> None:
        self.bot = bot
        self.category_description = _("""Commands for fun and distraction""")

    @staticmethod
    def category_emoji() -> PartialEmoji:
        return PartialEmoji(name="\N{VIDEO GAME}")

    @staticmethod
    def label() -> str:
        return _("Gimmicks")

    @staticmethod
    def category_title() -> str:
        return f"{Gimmicks.category_emoji}︱{Gimmicks.label}"

    @staticmethod
    def describe() -> bool:
        return False


#
############
