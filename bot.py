import asyncio
from importlib import reload

import discord
from discord.ext import commands

import cogs
import config
import helpers

DEFAULT_DISABLED_MESSAGE = (
    "Bot is currently down for maintenance."
    "Try again later."
)
AVG_DROPS_PER_DAY = 300

async def determine_prefix(bot, message):
    cog = bot.get_cog("Bot")
    return await cog.determine_prefix(message.guild)

def is_enabled(ctx):
    if not ctx.bot.enabled:
        raise commands.CheckFailure(
            DEFAULT_DISABLED_MESSAGE
        )
    return True

class ClusterBot(commands.AutoShardedBot):
    class Embed(discord.Embed):
        def __init__(self, **kwargs):
            color = kwargs.pop("color", 0xF44336)
            super().__init__(**kwargs, color=color)

    def __init__(self, **kwargs):
        self.pipe = kwargs.pop("pipe")
        self.cluster_name = kwargs.pop("cluster_name")
        self.cluster_idx = kwargs.pop("cluster_idx")
        self.config = config
        self.ready = False

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        super().__init__(**kwargs, loop=loop, command_prefix=determine_prefix)

        # Load extensions
        
        self.load_extension("jishaku")
        for i in cogs.default:
            self.load_extension(f"cogs.{i}")

        self.add_check(
            commands.bot_has_permissions(
                read_messages=True,
                send_messages=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                add_reactions=True,
                external_emojis=True,
            ).predicate
        )
        self.add_check(is_enabled)

        # Run bot

        self.log.info(
            f'[Cluster#{self.cluster_name}] {kwargs["shard_ids"]}, {kwargs["shard_count"]}'
        )

        self.loop.create_task(self.do_startup_tasks())
        self.run(kwargs["token"])

    # Easy access to things
    @property
    def pokemon(self):
        return self.get_cog("Pokemon")

    @property
    def embeds(self):
        return self.get_cog("Embeds")

    @property
    def db(self):
        return self.get_cog("Db")

    @property
    def log(self):
        return self.get_cog("Logging").log

    @property
    def enabled(self):
        for cog in self.cogs.values():
            try:
                if not cog.ready:
                    return False
            except AttributeError:
                pass
        return self.ready

    # Other stuff

    async def do_startup_tasks(self):
        await self.wait_until_ready()
        self.ready = True
        self.log.info(f"Logged in as {self.user}")

    async def on_ready(self):
        self.log.info(f"[Cluster#{self.cluster_name}] Ready called.")
        current_servers_in_db = await self.db.get_server_ids()
        bot_guilds = self.guilds
        self.log.info(f"{len(bot_guilds)} current servers")
        for server in bot_guilds:
            if str(server.id) not in current_servers_in_db:
                self.log.info(f"Added server: {str(server.id)} to db")
                await self.db.add_server(server)
        try:
            self.pipe.send(1)
            self.pipe.close()
        except OSError:
            pass

    async def on_shard_ready(self, shard_id):
        self.log.info(f"[Cluster#{self.cluster_name}] Shard {shard_id} ready")

    async def on_ipc_ready(self):
        self.log.info(f"[Cluster#{self.cluster_name}] IPC ready.")

    async def on_message(self, message: discord.Message):
        if message.author == self.user or message.author.bot or message.guild is None: # so bot doesnt respond to itself, another bot or a dm
            return

        # \\' fixes the no closing quotation when trying to process commands
        message.content = (
            message.content.replace("—", "--")
            .replace("′", "\\'")
            .replace("‘", "\\'")
            .replace("’", "\\'")
            .replace("'", "\\'")
        )

        try:
            await self.process_commands(message)
        except Exception as e:
            self.log.info(
            f'ERROR in on_message in /bot.py : {e}'
            )

        server_id = str(message.guild.id)
        if message.content.startswith(tuple(await determine_prefix(self, message))): # command so dont count
            await self.db.increment_user_interactions(str(message.author.id))
            await self.db.add_server_interactions_count(server_id)
            return
        await self.db.add_server_messages_count(server_id)
        # check if reached enough messages to drop a card
        total_server_messages = await self.db.get_server_messages_count(server_id)
        if total_server_messages: # if return a number correctly
            TO_DROP = 22 # minimum amt of messages to drop
            server_msgs_per_day = await self.db.get_server_msgs_per_day(server_id)
            # server msgs per day gets updated via aws lambda every day -- based on the past day
            if server_msgs_per_day / AVG_DROPS_PER_DAY > 22:
                TO_DROP = int(server_msgs_per_day / AVG_DROPS_PER_DAY)
            drop = total_server_messages % TO_DROP
            if drop == 0: # NUM_MSG_TO_DROP total messages since last drop
                await self.pokemon.card_drop(server_id) # card drop for the current server

    async def close(self):
        self.log.info("shutting down")
        await super().close()

    async def reload_modules(self):
        self.ready = False

        reload(cogs)
        reload(helpers)

        for i in dir(helpers):
            if not i.startswith("_"):
                reload(getattr(helpers, i))

        for i in cogs.default:
            self.reload_extension(f"cogs.{i}")

        await self.do_startup_tasks()
