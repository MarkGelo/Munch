import discord
from discord.ext import commands
from helpers import checks

class Configuration(commands.Cog):
    """Server Configuration"""

    def __init__(self, bot):
        self.bot = bot

    def make_config_embed(self, ctx, guild, commands={}):
        prefix = guild["prefix"] if guild["prefix"] is not None else "c!"
        if "channel" in guild:
            channel = int(guild["channel"])
            channels = [ctx.guild.get_channel(channel)] # in case i wanna add multiple channels to drop

        embed = self.bot.Embed()
        embed.title = "Server Configuration"
        embed.set_thumbnail(url=ctx.guild.icon_url)

        embed.add_field(
            name=f"Prefix {commands.get('prefix_command', '')}",
            value=f"`{prefix}`",
            inline=True,
        )

        if "channel" in guild:
            embed.add_field(
                name=f"Drop Channel {commands.get('set_dump_command', '')}",
                value="\n".join(map(lambda channel: channel.mention if channel else "Not set", channels)),
                inline=False,
            )

        return embed

    @commands.guild_only()
    @commands.group(
        name="configuration",
        aliases=["config"],
        invoke_without_command=True,
    )
    async def configuration(self, ctx: commands.Context):
        """Shows server configurations"""
        guild_prefix = await self.bot.db.get_server_prefix(str(ctx.guild.id))
        guild_channel_drop = await self.bot.db.get_server_channel_id_to_spam(str(ctx.guild.id))
        if guild_channel_drop:
            guild = {"prefix": guild_prefix, "channel": guild_channel_drop}
        else:
            guild = {"prefix": guild_prefix}

        embed = self.make_config_embed(ctx, guild)
        await ctx.send(embed=embed)

    @commands.guild_only()
    @configuration.command(name="help")
    async def advanced_configuration(self, ctx: commands.Context):
        """Server config + help"""
        
        guild_prefix = await self.bot.db.get_server_prefix(str(ctx.guild.id))
        prefix = guild_prefix if guild_prefix is not None else "p!"
        guild_channel_drop = await self.bot.db.get_server_channel_id_to_spam(str(ctx.guild.id))
        if guild_channel_drop:
            guild = {"prefix": prefix, "channel": guild_channel_drop}
        else:
            guild = {"prefix": prefix}
            
        commands = {
            "prefix_command": f"`{prefix}prefix <new prefix>`",
            "set_dump_command": f"`{prefix}set_dump`"
        }

        embed = self.make_config_embed(ctx, guild, commands)

        await ctx.send(embed=embed)

    @checks.is_admin_owner_manage_channels()
    @commands.guild_only()
    @commands.command()
    async def set_dump(self, ctx):
        """Set a channel where cards will be dropped on"""

        server_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        # test if can send a card in the channel
        chann = self.bot.get_channel(ctx.channel.id)
        if chann is None:
            out = {'type' : 'GENERAL', 'body' : 'Unable to send card in channel cuz bot cannot find the channel somehow',
                'footer': 'Requested by {}'.format(str(ctx.author)),
                'color': discord.Color.blue(), 'title': 'Changing dump channel'}
            await ctx.send(embed = await self.bot.embeds.get(out))
            return
        out = {'type' : 'GENERAL', 'body' : 'Pokemon cards will now drop in {}'.format(str(ctx.channel)),
                'footer': 'Requested by {}'.format(str(ctx.author)),
                'color': discord.Color.blue(), 'title': 'Changed dump channel'}
        await ctx.send(embed = await self.bot.embeds.get(out))
        await self.bot.db.update_server_channel_id_to_spam(server_id, channel_id)

    @checks.is_admin_owner_manage_channels()
    @commands.guild_only()
    @commands.command()
    async def prefix(self, ctx: commands.Context, *, prefix: str = None):
        """Change the bot prefix"""
        
        if prefix is None:
            guild_prefix = await self.bot.db.get_server_prefix(str(ctx.guild.id))
            return await ctx.send(f"The prefix is `{guild_prefix if guild_prefix is not None else 'p!'}` in this server")

        if prefix in ("reset", "p!", "P!"):
            await self.bot.db.update_server_prefix(str(ctx.guild.id), prefix)
            self.bot.prefixes[ctx.guild.id] = None

            return await ctx.send("Reset prefix to `p!` for this server.")

        if len(prefix) > 100:
            return await ctx.send("Prefix is too long")

        await self.bot.db.update_server_prefix(str(ctx.guild.id), prefix)
        self.bot.prefixes[ctx.guild.id] = prefix

        await ctx.send(f"Changed prefix to `{prefix}` for this server.")

def setup(bot):
    bot.add_cog(Configuration(bot))
