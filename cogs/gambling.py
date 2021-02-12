import discord
from discord.ext import commands
import numpy as np
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

'''
SLOTS = [
    emojis['WATER'], emojis['METAL'], emojis['FIRE'], emojis['FIGHTING'],
    emojis['DARKNESS'], emojis['PSYCHIC'], emojis['LIGHTNING'], emojis['GRASS'],
    emojis['FAIRY'], emojis['COLORLESS'], emojis['DRAGON']
]
'''
SLOTS = [
    emojis['WATER'], emojis['LIGHTNING'], emojis['GRASS'], emojis['COLORLESS']
]
# Water 325, Psychic 362, Metal 178, Lightning 212, Grass 242, Fire 248
# Fighting 225, Fairy 78, Dragon 171, Darkness 189, Colorless 237


class Gambling(commands.Cog):
    """Economy"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def slots(self, ctx):
        """Earn rare+ cards through gambling on slots"""

        # costs 100
        # 4 ELEMENTS
        # 0: 85%, 1: 13%, 2: 1% -- NOT IN SERVER
        # 0: 78%, 1: 18%, 2: 2% -- IN SERVER
        SLOTS_COST = 100
        # check if enough money
        user_money = await self.bot.db.get_money(ctx.author)
        if user_money - SLOTS_COST < 0:
            #not enough money
            await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Not enough money', 'color': discord.Color.gold(),
                                                'footer': f'Poor gambling addict -> {str(ctx.author)}',
                                                'body': 'You need **$100** to do slots'}))
            return
        # subtract money
        await self.bot.db.subtract_money(ctx.author, SLOTS_COST)
        # Slots mechanism
        random.shuffle(SLOTS)
        server_advantage = 1.5
        mach = [np.random.choice(SLOTS, p = [1/len(SLOTS)] * len(SLOTS) if ctx.guild.id != 725921184541310996 else [server_advantage/len(SLOTS)] + [(1-server_advantage/len(SLOTS))/(len(SLOTS)-1)]*(len(SLOTS)-1)) for i in range(16)]
        machine = divideList(mach, 4)
        win_show = [[':x:',':x:',':x:'],[':x:',':x:',':x:'],[':x:',':x:'],[':x:',':x:']]
        wins = slots_wins(machine)
        win_poke = []
        for win in wins:
            win_show[win['type'][1]][win['type'][0]] = ':white_check_mark:'
            win_poke.append(win['poke'])
        increased = "" # '**Increased Rates** in Nowhere for now' if ctx.guild.id != 725921184541310996 else '**Increased Rates**'
        embed = {'type': 'GENERAL', 'title': ':slot_machine: SLOT MACHINE :slot_machine:', 'color': discord.Color.gold(),
                    'footer': 'Elements rotate weekly',
                    'body': f'You spent **$100** to lose??\n{increased}',
                    'fields': [
                        {'type': f"{emojis['NONE']}", 'inline': True, 'body': '\n'.join([' '.join(x) for x in machine])},
                        {'type': ":point_left: :point_down: :french_bread:", 'inline': True,
                        'body': '\n'.join([' '.join(x) for x in win_show])}
                    ]}
        await ctx.send(embed = await self.bot.embeds.get(embed))

        for pokemon in win_poke:
            # give to user
            poke_type = pokemon.split(':')[1]
            card = await self.bot.db.random_card(type_ = poke_type, rarity = 'rare+')
            await self.bot.db.add_user_card(ctx.author, card['id'])
            # send message about the card as well
            picture_file = discord.File('data/images/{}.webp'.format(card['id']), filename = 'won.webp')
            embed = {'type': 'GENERAL-ATTACHMENT-IMAGE', 'body': '', 'title': 'You won -- {} | {}'.format(card['name'], card['id']),
                        'color': discord.Color.green(), 'footer': 'Gambling is good?',
                        'attachment': 'won.webp'}
            await ctx.send(embed = await self.bot.embeds.get(embed), file = picture_file)

    @commands.command()
    async def gamble(self, ctx, amount):
        """Gamble money with 50% chance to win"""
        
        try:
            amt = int(amount)
        except:
            await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Invalid amount', 'footer': 'why',
                                                'color': discord.Color.blue(),
                                                'body': f'{amount} is not an integer'}))
            return
        if amt <= 0:
            await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Invalid amount', 'footer': 'why',
                                                'color': discord.Color.blue(),
                                                'body': 'Amount has to be greater than 0'}))
            return
        #check if user has enough money
        user_money = await self.bot.db.get_money(ctx.author)
        if user_money - amt < 0:
            # not enough money
            await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Not enough money', 'color': discord.Color.gold(),
                                                'footer': f'Poor gambling addict -> {str(ctx.author)}',
                                                'body': f'You need to have **${amt}** to be able to gamble it'}))
            return

        win = bool(random.getrandbits(1))
        if not win:
            await self.bot.db.subtract_money(ctx.author, amt)
            await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'You LOST', 'color': discord.Color.gold(),
                                                'footer': f'Unlucky gambling addict -> {str(ctx.author)}',
                                                'body': f'You gambled **${amt}** and lost **${amt}**\nYou now have **${user_money - amt}**'}))
            return
        earned = int(amt * random.uniform(0.1, 1))
        await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'You Won', 'color': discord.Color.gold(),
                                                'footer': f'Lucky gambling addict -> {str(ctx.author)}',
                                                'body': f'You gambled **${amt}** and won **${earned}**\nYou now have **${user_money + earned}**'}))
        #give user money
        await self.bot.db.add_money(ctx.author, earned)

def slots_wins(arr):
    wins = []
    # (0,1) means horizontal, second row
    # (1,0) means vertical, first row
    # (2,0) means diagonal /
    for i in range(len(arr)):
        if arr[0][i] == arr[1][i] and arr[1][i] == arr[2][i] and arr[2][i] == arr[3][i]:
            #vertical
            wins.append({'type': (1, i), 'poke': arr[0][i]})
        if arr[i][0] == arr[i][1] and arr[i][1] == arr[i][2] and arr[i][2] == arr[i][3]:
            #horizontal win
            wins.append({'type': (0, i), 'poke': arr[i][0]})
    if arr[0][0] == arr[1][1] and arr[1][1] == arr[2][2] and arr[2][2] == arr[3][3]:
        #diagonal \
        wins.append({'type': (2, 0), 'poke': arr[0][0]})
    if arr[0][3] == arr[1][2] and arr[1][2] == arr[2][1] and arr[2][1] == arr[3][0]:
        #diagonal /
        wins.append({'type': (2, 1), 'poke': arr[0][3]})
    return wins

def divideList(arr, n): # n is the size to divide by, n = 50 makes teh arr into 50 size arrays in a list
    out = []
    for i in range(0, len(arr), n):
        out.append(arr[i : i + n])
    return out

def setup(bot):
    bot.add_cog(Gambling(bot))