import asyncio

import discord
from discord.ext import commands

paginators = {}

# a lil bit wonky -- but better than nothing

class Paginator:
    def __init__(self, get_page, num_pages):
        self.num_pages = num_pages
        self.get_page = get_page
        self.last_page = 0
        self.message = None
        self.author = None

    async def delete(self):
        try:
            await self.message.delete()
        except:
            pass

    async def end(self):
        try:
            del paginators[self.author.id]
        except:
            pass

    async def send(self, bot, ctx: commands.Context, pidx: int):
        async def clear(msg):
            return await ctx.send(msg)

        self.author = ctx.author

        paginators[self.author.id] = self

        embed_ = await self.get_page(pidx, clear)
        pic_file = None

        if isinstance(embed_, tuple):
            embed, pic_file = embed_
        else:
            embed = embed_

        if not isinstance(embed, discord.Embed):
            return
        
        prefix = "@Munch " if ctx.prefix in [bot.user.mention + " ",
            bot.user.mention[:2] + "!" + bot.user.mention[2:] + " "] else ctx.prefix

        try:
            embed.set_footer(
                text=embed.footer.text
                + f"\nUse '{prefix}n' and '{prefix}b' to navigate between pages"
            )
        except TypeError:
            embed.set_footer(
                text=f"\nUse '{prefix}n' and '{prefix}b' to navigate between pages"
            )
        self.message = await ctx.send(embed=embed, file = pic_file) if pic_file else await ctx.send(embed = embed)
        self.last_page = pidx