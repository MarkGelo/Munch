import random
import typing
from datetime import datetime

import discord
from discord.ext import commands, flags
from helpers import pagination, constants, checks
import math

class Administration(commands.Cog):
    """Bot Administration"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command(aliases = ["reload.cogs"])
    async def reload_cogs(self, ctx: commands.Context):
        """Reload all cogs"""
        await ctx.send("Reloaded modules")
        await self.bot.reload_modules()

    @flags.add_flag("page", nargs="?", type=int, default=1)
    @flags.add_flag('--id', nargs="?", type=int, default=None)
    @flags.add_flag('--answer', nargs="+", type=str, default=None)
    @flags.add_flag('--close', action = 'store_true')
    
    # for sorting
    @flags.add_flag('--error', action = 'store_true')
    @flags.add_flag('--help', action = 'store_true')
    @flags.add_flag('--suggestion', action = 'store_true')
    @flags.commands.is_owner()
    @flags.command()
    async def support(self, ctx: commands.Context, **flags):
        """Support Tickets Functions"""
        #print(flags)
        if 'answer' in flags and flags['answer'] and flags['close']:
            return await ctx.send("Can only do one at a time. `--answer` `--close`")
        elif 'answer' in flags and flags['answer']:
            # bot sends answer to user who sent the support ticket and closes it
            if 'id' not in flags and not flags['id']:
                return await ctx.send("Please indicate the id with the answer. `--id <id> --answer <message>`")
            answer = ' '.join(flags['answer'])
            cursor = self.bot.db.connection.cursor()
            cursor.execute("SELECT id, user_id, flags, message FROM support WHERE id = %s", flags['id'])
            out = cursor.fetchone()
            cursor.execute("DELETE FROM support where id = %s", flags['id'])
            self.bot.db.connection.commit()
            cursor.close()
            if out:
                embed = self.bot.Embed(color = 0x6CFF00)
                embed.title = f"Support Ticket Closed"
                embed.description = '\n'.join([
                    f"**ID:** {out[0]}",
                    f"**From user:** {'<@' + str(out[1]) + '>'}",
                    f"**Type:** {out[2]}",
                    f"**Message:** {out[3]}",
                    f"**Response:** {answer}"
                ])
                await ctx.send(embed = embed)
                # send dm
                member = self.bot.get_user(int(out[1]))
                if member:
                    return await member.send(embed = embed)
                else:
                    return await ctx.send("Closed ticket however user was not found. Bot is not in any server with the user!")
            else:
                return await ctx.send(f"No support ticket found with ID: {flags['id']}")
        elif 'id' in flags and flags['id'] and not flags['close']:
            cursor = self.bot.db.connection.cursor()
            cursor.execute("SELECT id, user_id, flags, message FROM support WHERE id = %s", flags['id'])
            out = cursor.fetchone()
            cursor.close()
            if out:
                embed = self.bot.Embed(color = 0x6CFF00)
                embed.title = f"Support Ticket"
                embed.description = f"**ID:** {out[0]}\n**Type:** {out[2]}\n**Message:** {out[3]}"
                return await ctx.send(embed = embed)
            else:
                return await ctx.send(f"No support ticket found with ID: {flags['id']}")
        elif flags['close'] and 'id' in flags and flags['id']:
            cursor = self.bot.db.connection.cursor()
            cursor.execute("DELETE FROM support where id = %s", flags['id'])
            self.bot.db.connection.commit()
            cursor.close()
            return await ctx.send(f"Support ID {flags['id']} closed")
        # list support tickets
        num = await self.bot.db.get_support_tickets(flags, count = True)
        if num == 0:
            return await ctx.send("No support tickets found")
        async def get_page(pidx, clear):
            pgstart = pidx * 20

            s_tickets = await self.bot.db.get_support_tickets(flags, pgstart, 20)

            if len(s_tickets) == 0:
                return await ctx.send('No tickets on this page')
            
            page = [
                f"`{s['id']}` | {s['flags']} | **{s['message'][:30]}**" 
                for s in s_tickets
            ]

            embed = self.bot.Embed(color = discord.Color.dark_teal())
            embed.title = "Support Tickets"
            embed.description = '\n'.join(page)[:2048] # limit in embed
            embed.set_footer(text = f"Page {pidx+1} of {math.ceil(num/20)}")
            return embed
        paginator = pagination.Paginator(get_page, num_pages = math.ceil(num / 20))
        await paginator.send(self.bot, ctx, flags['page'] - 1)


def setup(bot: commands.Bot):
    bot.add_cog(Administration(bot))
