import itertools

import discord
from discord.ext import commands, flags
from helpers import pagination
import random

class CustomHelpCommand(commands.HelpCommand):
    """Help"""
    def __init__(self):
        super().__init__(
            command_attrs={"help": "Information about the commands, categories and functions of the bot"}
        )

    async def on_help_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(str(error.original))

    def make_page_embed(
        self, commands, title="Munch Help", description=discord.Embed.Empty
    ):
        embed = self.context.bot.Embed(color=0xE67D23)
        embed.title = title
        embed.description = description
        embed.set_footer(
            text=f'Use "{self.clean_prefix}help <command>" for more information'
        )

        for command in commands:
            signature = self.clean_prefix + command.qualified_name + " "

            signature += (
                "[args...]"
                if isinstance(command, flags.FlagCommand)
                else command.signature
            )

            embed.add_field(
                name=signature,
                value=command.help or "No help for u",
                inline=False,
            )

        return embed

    def make_default_embed(
        self, cogs, title="Munch Categories", description=discord.Embed.Empty
    ):
        embed = self.context.bot.Embed(color=0xE67D23)
        embed.title = title
        embed.description = description

        counter = 0
        for cog in cogs:
            cog, description, command_list = cog
            if cog is None:
                continue
            description = f"{''.join([f'`{command.qualified_name}` ' for command in command_list])}"
            embed.add_field(name=cog.qualified_name, value=description, inline=True)
            counter += 1

        return embed

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        def get_category(command):
            cog = command.cog
            return cog.qualified_name if cog is not None else "\u200bNo Category"

        cogs = []
        total = 0

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        for cog_name, commands in itertools.groupby(filtered, key=get_category):
            commands = sorted(commands, key=lambda c: c.name)

            if len(commands) == 0:
                continue

            total += len(commands)
            cog = bot.get_cog(cog_name)
            description = (
                (cog and cog.description)
                if (cog and cog.description) is not None
                else discord.Embed.Empty
            )
            cogs.append((cog, description, commands))
        
        embed = self.make_default_embed(
                cogs,
                title=f"Munch Commands",
                description=(
                    f"Use `{self.clean_prefix}help <command/category>` for more information"
                ),
            )

        await ctx.send(embed = embed)

    async def send_cog_help(self, cog):
        ctx = self.context
        bot = ctx.bot

        filtered = await self.filter_commands(cog.get_commands(), sort=True)

        embed = self.make_page_embed(
            filtered,
            title=(cog and cog.qualified_name or "Other") + " Commands",
            description=discord.Embed.Empty if cog is None else cog.description,
        )

        await ctx.send(embed=embed)

    async def send_group_help(self, group):
        ctx = self.context
        bot = ctx.bot

        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        filtered = await self.filter_commands(subcommands, sort=True)

        embed = self.make_page_embed(
            filtered,
            title=group.qualified_name,
            description=f"{group.description}\n\n{group.help}"
            if group.description
            else group.help or "No help for u",
        )

        await ctx.send(embed=embed)

    async def send_command_help(self, command):
        embed = self.context.bot.Embed(color=0xE67D23)
        embed.title = self.clean_prefix + command.qualified_name

        if command.description:
            embed.description = f"{command.description}\n\n{command.help}"
        else:
            embed.description = command.help or "No help for u"

        embed.add_field(name="Command", value=self.get_command_signature(command))

        await self.context.send(embed=embed)

def setup(bot):
    bot.old_help_command = bot.help_command
    bot.help_command = CustomHelpCommand()

def teardown(bot):
    bot.help_command = bot.old_help_command