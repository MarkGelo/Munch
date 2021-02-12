import random
import sys
import traceback
from datetime import datetime, timedelta

import aiohttp
import discord
from discord.ext import commands, flags, tasks
from discord.ext.commands.errors import CheckFailure
from helpers import pagination


class Bot(commands.Cog):
    """Basic Functions"""
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(self.bot, "prefixes"):
            self.bot.prefixes = {}

        self.update_status.start()
        if self.bot.cluster_idx == 0:
            self.post_dbl.start()
            self.post_dbotsgg.start()
            #self.remind_votes.start()

    @tasks.loop(minutes = 10)
    async def post_dbl(self): # top.gg
        await self.bot.wait_until_ready()
        if not self.bot.config.DBL_TOKEN:
            return
        headers = {"Authorization": self.bot.config.DBL_TOKEN}
        data = {"server_count": len(self.bot.guilds), "shard_count": len(self.bot.shards)}
        async with aiohttp.ClientSession(headers=headers) as sess:
            r = await sess.post(
                f"https://top.gg/api/bots/{self.bot.user.id}/stats", data=data
            )
    
    @tasks.loop(minutes = 10)
    async def post_dbotsgg(self): # discord.bots.gg
        await self.bot.wait_until_ready()
        if not self.bot.config.DBOTSGG_TOKEN:
            return
        headers = {"Authorization": self.bot.config.DBOTSGG_TOKEN}
        data = {"guildCount": len(self.bot.guilds), "shardCount": len(self.bot.shards)}
        async with aiohttp.ClientSession(headers=headers) as sess:
            r = await sess.post(
                f"https://discord.bots.gg/api/v1/bots/{self.bot.user.id}/stats", data=data
            )

    @tasks.loop(minutes = 5)
    async def update_status(self):
        await self.bot.wait_until_ready()
        
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.bot.guilds)} servers",
            )
        )

    @commands.Cog.listener()
    async def on_command(self, ctx):
        self.bot.log.info(
            f'COMMAND {ctx.author.id} {ctx.command.qualified_name}: {ctx.author} "{ctx.message.content}"'
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            self.bot.log.info(f"{ctx.author.id} cooldown")
            await ctx.message.add_reaction("⏳")
            await ctx.message.add_reaction("🆒")
            await ctx.message.add_reaction("⬇️")
        elif isinstance(error, commands.MaxConcurrencyReached):
            name = error.per.name
            suffix = "per %s" % name if error.per.name != "default" else "globally"
            plural = "%s times %s" if error.number > 1 else "%s time %s"
            fmt = plural % (error.number, suffix)
            await ctx.send(f"This command can only be used {fmt} at the same time. Please wait for a couple of seconds.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command cannot be used in private messages")
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("Command is disabled and cannot be used")
        elif isinstance(error, commands.BotMissingPermissions):
            missing = [
                "`" + perm.replace("_", " ").replace("guild", "server").title() + "`"
                for perm in error.missing_perms
            ]
            fmt = "\n".join(missing)
            message = f"💥 I need the following permissions to run this command:\n{fmt}\nPlease fix and try again."
            botmember = (
                self.bot.user
                if ctx.guild is None
                else ctx.guild.get_member(self.bot.user.id)
            )
            if ctx.channel.permissions_for(botmember).send_messages:
                await ctx.send(message)
            else: # send dm to user to whom used this command
                member = self.bot.get_user(ctx.author.id)
                await member.send('\n'.join([
                    "Sorry for this DM!",
                    "However you used a command and I was unable to reply due to missing permissions in that channel.",
                    "Some/All of the permissions I am missing are:",
                    f"{fmt}",
                    "It's most likely the `Send Messages` permissions that is causing this issue."
                ]))
                self.bot.log.info(
                f'ERROR (SENT DM) {ctx.command} : {error}'
                )
        elif isinstance(
            error,
            (
                commands.CheckFailure,
                commands.UserInputError,
                flags.ArgumentParsingError,
            ),
        ):
            await ctx.send(error)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send_help(ctx.command)
        elif isinstance(error, commands.CommandNotFound):
            return
        else:
            print(f"Ignoring exception in command {ctx.command}")
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )
            print("\n\n")
            self.bot.log.info(
            f'ERROR {ctx.command} : {error}'
            )

    @commands.Cog.listener()
    async def on_error(self, ctx: commands.Context, error):

        if isinstance(error, discord.NotFound):
            return
        else:
            print(f"Ignoring exception in command {ctx.command}:")
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )
            print("\n\n")
            self.bot.log.info(
            f'ERROR {ctx.command} : {error}"'
            )

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.bot.db.add_server(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.bot.db.delete_server(str(guild.id))

    @flags.add_flag("message", nargs="+", type=str, default=None)
    @flags.add_flag('--error', action = 'store_true')
    @flags.add_flag('--help', action = 'store_true')
    @flags.add_flag('--suggestion', action = 'store_true')
    @flags.commands.cooldown(1, 5*60, commands.BucketType.user) # 5 minutes cooldown
    @flags.command()
    async def support_ticket(self, ctx: commands.Context, **flags):
        """Contact Developer by making a support ticket
        Available Tags -> `--error` `--help` `--suggestion`
        `<prefix> <message> --error` will notify developer about an error
        `<prefix> --help <message>` will notify developer of the help you need"""
        true_f = [k for k,v in flags.items() if v and k != "message"]
        if not true_f:
            return await ctx.send("Please add a type for your ticket/message| `--error` `--help` `--suggestion`\nUse command `help send` for more info")
        flags['message'] = ' '.join(flags['message'])
        flags['user_id'] = str(ctx.author.id)
        flags['flags'] = ', '.join(true_f)
    
        cursor = self.bot.db.connection.cursor()
        cursor.execute("INSERT INTO support(user_id, flags, message) VALUES (%(user_id)s, %(flags)s, %(message)s)", flags)
        cursor.close()

        embed = self.bot.Embed(color = 0x6CFF00)
        embed.title = f"Support Ticket Sent"
        embed.description = f"**Type:** {flags['flags']}\n\n**Message:** {flags['message']}"
        await ctx.send(embed = embed)

    @commands.command(aliases=["n", "forward"])
    async def next(self, ctx: commands.Context):
        """Go to the next page of a paginated embed"""

        if ctx.author.id not in pagination.paginators:
            return await ctx.send("Couldn't find your previous message")

        paginator = pagination.paginators[ctx.author.id]

        if paginator.num_pages == 0:
            return

        pidx = paginator.last_page + 1
        pidx %= paginator.num_pages

        await paginator.send(self.bot, ctx, pidx)

    @commands.command(aliases=["prev", "back", "b"])
    async def previous(self, ctx: commands.Context):
        """Go to the previous page of the paginated embed"""

        if ctx.author.id not in pagination.paginators:
            return await ctx.send("Couldn't find your previous message")

        paginator = pagination.paginators[ctx.author.id]

        if paginator.num_pages == 0:
            return

        pidx = paginator.last_page - 1
        pidx %= paginator.num_pages

        await paginator.send(self.bot, ctx, pidx)

    @commands.command(aliases=["l"])
    async def last(self, ctx: commands.Context):
        """Go to the last page in paginated embed"""

        if ctx.author.id not in pagination.paginators:
            return await ctx.send("Couldn't find your previous message")

        paginator = pagination.paginators[ctx.author.id]
        await paginator.send(self.bot, ctx, paginator.num_pages - 1)

    @commands.command(aliases=["page", "g"])
    async def go(self, ctx: commands.Context, page: int):
        """Go to a certain page in paginated embed"""

        if ctx.author.id not in pagination.paginators:
            return await ctx.send("Couldn't find your previous message")

        paginator = pagination.paginators[ctx.author.id]

        if paginator.num_pages == 0:
            return

        await paginator.send(self.bot, ctx, page % paginator.num_pages)

    async def determine_prefix(self, guild):
        if guild:
            if guild.id not in self.bot.prefixes:
                prefix = await self.bot.db.get_server_prefix(str(guild.id))
                if prefix is None: # if prefix none then not on db, add server to db
                    # TODO go to get_server_prefix and change to return None if error
                    pass
                self.bot.prefixes[guild.id] = prefix

            if self.bot.prefixes[guild.id] is not None:
                return [
                    self.bot.prefixes[guild.id],
                    self.bot.user.mention + " ",
                    self.bot.user.mention[:2] + "!" + self.bot.user.mention[2:] + " ",
                ]

        return [
            "p!",
            "P!",
            self.bot.user.mention + " ",
            self.bot.user.mention[:2] + "!" + self.bot.user.mention[2:] + " ",
        ]
    
    @commands.command()
    async def ping(self, ctx: commands.Context):
        """View bot's latency"""

        message = await ctx.send("Pong!")
        ms = int((message.created_at - ctx.message.created_at).total_seconds() * 1000)

        if ms > 300 and random.random() < 0.25:
            await message.edit(
                content=(
                    f"Pong! **{ms} ms**\n"
                    "bot do be lagging\n\n"
                    "Interested in more Trading Card Games? Consider checking out Kyuu!\n"
                    "https://top.gg/bot/777894474079666227"
                )
            )
        else:
            await message.edit(content=f"Pong! **{ms} ms**")

    @commands.command()
    async def vote(self, ctx: commands.Context):
        """Shows how to vote"""

        out = {'type' : 'GENERAL', 'body' : '[Voting](https://top.gg/bot/717368969102622770/vote) will give you **$400**\n**May take a couple of minutes**', 
                    'footer': 'Requested by {}'.format(str(ctx.author)),
                    'color': discord.Color.blue(), 'title': 'Vote for money'}
        await ctx.send(embed = await self.bot.embeds.get(out))

    @commands.command()
    async def invite(self, ctx: commands.Context):
        """Show invite links"""

        embed = self.bot.Embed(color=0xf1c40f)
        embed.title = "Invite this bot"
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(
            name="Invite Link", value="https://top.gg/bot/717368969102622770", inline=False
        )

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Bot(bot))