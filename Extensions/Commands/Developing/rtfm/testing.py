############
#
from re import IGNORECASE, compile, escape, sub
from time import time
from typing import Callable, Iterable, List, Optional

from discord import Member
from discord.abc import Messageable

from Classes import Format, ShakeCommand, ShakeEmbed, Types, _

########
#


def finder(
    text: str,
    collection: Iterable[str],
    *,
    key: Optional[Callable[[str], str]] = ...,
    lazy: bool = True,
) -> list[str]:
    suggestions: list[tuple[int, int, str]] = []
    text = str(text)
    pat = ".*?".join(map(escape, text))
    regex = compile(pat, flags=IGNORECASE)
    for item in collection:
        to_search = key(item) if key else item
        r = regex.search(to_search)
        if r:
            suggestions.append((len(r.group()), r.start(), item))

    def sort_key(tup: tuple[int, int, str]) -> tuple[int, int, str]:
        if key:
            return tup[0], tup[1], key(tup[2])
        return tup

    if lazy:
        return (z for _, _, z in sorted(suggestions, key=sort_key))
    else:
        return [z for _, _, z in sorted(suggestions, key=sort_key)]


class command(ShakeCommand):
    async def __await__(self, key, obj: str = None):
        assert bool(self.bot.cache["rtfm"])
        manuals = Types.Manuals.value[key]
        await self.ctx.defer()
        if obj is None:
            return await self.ctx.chat(manuals["url"])

        start = time() * 1000
        obj = sub(r"^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)", r"\1", obj)
        if key.startswith("latest"):
            l = obj.lower()
            if l in dir(Messageable):
                obj = f"abc.Messageable.{l}"
        cache = set(self.bot.cache["rtfm"][key].items())
        matches = finder(obj, cache, key=lambda t: t[0], lazy=False)[:10]
        completed = time() * 1000 - start
        if len(matches) == 0:
            return await self.ctx.chat(_("Couldn't find anything."))
        embed = ShakeEmbed.default(
            self.ctx,
            title=_("RTFM results on search „{query}“").format(query=obj)
            if obj
            else None,
            description="\n".join(
                Format.list(f"[`{key}`]({url})") for key, url in matches
            ),
        )
        embed.set_author(
            icon_url=manuals.get("icon", None),
            name=manuals.get("name", key.capitalize()),
            url=manuals.get("url", None),
        )
        embed.set_thumbnail(url=manuals.get("icon", None))
        embed.set_footer(
            icon_url=embed.footer.icon_url,
            text=" • ".join((f"{completed:.0f}ms", (embed.footer.text or str()))),
        )
        await self.ctx.chat(embed=embed)
        await self.bot.pool.execute(
            "INSERT INTO rtfm (user_id) VALUES ($1) ON CONFLICT (user_id) DO UPDATE SET count = rtfm.count + 1;",
            self.ctx.author.id,
        )
        return

    async def stats(self, member: List[Member] = None):
        """Tells you stats about the ?rtfm command."""
        self.member: List[Member] = member
        query = "SELECT SUM(count) AS total_uses FROM rtfm;"
        record = await self.bot.pool.fetchrow(query)
        total_uses: int = record["total_uses"]

        if self.member is not None:
            embed = ShakeEmbed.default(
                self.ctx,
            )
            embed.set_author(
                name="RTFM Stats {prefix} {user_names}".format(
                    prefix=self.bot.emojis.prefix, user_names=", ".join(self.member)
                ),
                icon_url=self.bot.user.display_avatar.url,
            )
            query = "SELECT count FROM rtfm WHERE user_id=$1;"
            for m in self.member:
                record = await self.bot.pool.fetchrow(query, m.id)
                count = 0 if record is None else record["count"]
                embed.add_field(name=_("Uses"), value=count, inline=False)
                embed.add_field(
                    name=_("Total", value=f"{count/total_uses:.0%} von {total_uses}"),
                    inline=False,
                )
            await self.ctx.chat(embed=embed)
            return

        query = "SELECT user_id, count FROM rtfm ORDER BY count DESC LIMIT 10;"
        records = await self.bot.pool.fetch(query)
        output = []
        if total_uses is None:
            return await self.ctx.chat("Keine Einträge")
        output.append(
            Format.bold(_("Total uses: {total_uses}").format(total_uses=total_uses))
        )

        if records:
            output.append(Format.bold(_("Top {top} member:").format(top=len(records))))
            for rank, (user_id, count) in enumerate(records, 1):
                user = self.bot.get_user(user_id) or (
                    await self.bot.fetch_user(user_id)
                )
                if rank != 10:
                    output.append(f"{rank}\u20e3 {user}: {count}")
                else:
                    output.append(f"\N{KEYCAP TEN} {user}: {count}")

        await self.ctx.chat("\n".join(output))


#
############