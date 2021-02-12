import discord
from discord.ext import commands
import random

emojis = {
'NONE': '<:None:722275990205890590>',
'RARER' : ':star:',
'COLORLESS' : '<:colorless:719640131350560860>',
'DARKNESS' : '<:darkness:719640131530653697>',
'BUG' : '<:bug:719640131551887370>',
'FIRE' : '<:fire:719640132508188702>',
'FLYING' : '<:flying:719640132520771615>',
'GHOST' : '<:ghost:719640132541743104>',
'DRAGON' : '<:dragon:719640132797595720>',
'LIGHTNING' : '<:lightning:719640132877156412>',
'FAIRY' : '<:fairy:719640132969562224>',
'GRASS' : '<:grass:719640133002985512>',
'GROUND' : '<:ground:719640133019893891>',
'METAL' : '<:metal:719640133070094438>',
'POISON' : '<:poison:719640133124489278>',
'ROCK' : '<:rock:719640133170757673>',
'FIGHTING' : '<:fighting:719640133196054598>',
'ICE' : '<:ice:719640133216895076>',
'WATER' : '<:water:719640133237866496>',
'PSYCHIC' : '<:psychic:719640133267095693>',
'COMMON' : '<:common:719640157598253087>',
'RARE' : '<:rare:719640157950836836>',
'UNCOMMON' : '<:uncommon:719640157992517673>'}


class Embeds(commands.Cog):
    """Embed Functions"""
    def __init__(self, bot):
        self.bot = bot

    async def get(self, text):
        text_type = text['type']
        if text_type == 'GENERAL':
            embed = discord.Embed(
                title = text['title'],
                description = text['body'],
                color = text['color']
            ).set_footer(text = text['footer'])
            if 'fields' in text:
                for field in text['fields']:
                    embed.add_field(name = field['type'], value = field['body'], inline = field['inline'] if 'inline' in field else True)
            return embed
        elif text_type == 'GENERAL-ATTACHMENT-IMAGE': # for pokemon card drops
            embed = discord.Embed(
                title = text['title'],
                description = text['body'],
                color = text['color']
            ).set_footer(text = '{}'.format(text['footer']))
            embed.set_image(url = 'attachment://{}'.format(text['attachment']))
            return embed
        elif text_type == 'GENERAL-ATTACHMENT-THUMBNAIL':
            embed = discord.Embed(
                title = text['title'],
                description = text['body'],
                color = text['color']
            ).set_footer(text = '{}'.format(text['footer']))
            embed.set_thumbnail(url = 'attachment://{}'.format(text['attachment']))
            if 'stats' in text:
                for stats in text['stats']:
                    # add emoji next to name
                    field_name = stats
                    if stats == 'None':
                        field_name = 'None'
                    elif stats == 'Common':
                        field_name = 'Common {}'.format(emojis['COMMON'])
                    elif stats == 'Uncommon':
                        field_name = 'Uncommon {}'.format(emojis['UNCOMMON'])
                    elif stats == 'Rare':
                        field_name = 'Rare {}'.format(emojis['RARE'])
                    else:
                        field_name = '{} {}'.format(stats, emojis['RARER'])
                    embed.add_field(name = field_name, value = text['stats'][stats], inline = True)
            return embed
        elif text_type == 'GENERAL-THUMBNAIL':
            embed = discord.Embed(
                title = text['title'],
                description = text['body'],
                color = text['color']
            ).set_footer(text = '{}'.format(text['footer']))
            embed.set_thumbnail(url = text['thumbnail'])
            if 'stats' in text:
                for stats in text['stats']:
                    # add emoji next to name
                    field_name = stats
                    if stats == 'None':
                        field_name = 'None'
                    elif stats == 'Common':
                        field_name = 'Common {}'.format(emojis['COMMON'])
                    elif stats == 'Uncommon':
                        field_name = 'Uncommon {}'.format(emojis['UNCOMMON'])
                    elif stats == 'Rare':
                        field_name = 'Rare {}'.format(emojis['RARE'])
                    else:
                        field_name = '{} {}'.format(stats, emojis['RARER'])
                    embed.add_field(name = field_name, value = text['stats'][stats], inline = True)
            return embed
        else:
            return discord.Embed(
                body = 'I suck'
            ).set_footer(text = 'im bad at coding')

def setup(bot):
    bot.add_cog(Embeds(bot))