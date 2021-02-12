import discord
from discord.ext import commands, flags, tasks
from helpers import checks, constants, pagination
import math
import random

class Market(commands.Cog):
    """Marketplace"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def store(self, ctx: commands.Context):
        """Show store"""

        store_embed = { 'type': 'GENERAL', 'title': 'Pokemon Card Store', 'user': str(ctx.author),
                        'footer': random.choice(constants.FOOTERS), 'color': discord.Color.dark_purple(),
                        'body': '\n'.join('{} | **${}** | {}'.format(item['name'], item['cost'], item['description']) for item in constants.STORE)}
        store_embed['body'] += f'\n\nDo `{ctx.prefix}store.buy <name>` with the name of the item you want to buy'
        await ctx.send(embed = await self.bot.embeds.get(store_embed))
    
    @commands.command(aliases = ['store.buy'])
    async def store_buy(self, ctx: commands.Context, *, item):
        """Buy an item from the store"""

        bought = await self.bot.db.buy(ctx.author, item)
        random_card = bought[0]['id'] if bought else None # get first card in list of cards -- min 1 so its fine, max 10 -- shuffles if 10 so rng
        if bought:
            picture_file = discord.File(f'data/images/{random_card}.webp', filename = 'card.webp')
            embed = {   'type': 'GENERAL-ATTACHMENT-IMAGE', 'title': 'Bought {}'.format(item),
                        'footer': random.choice(constants.FOOTERS), 'color': discord.Color.dark_red(),
                        'body': '\n'.join('{} {} | **{}** | {} | {}'.format(self.bot.pokemon.get_rarity_emoji(card['rarity']),
                                                                ''.join(self.bot.pokemon.get_energy_types_emoji(card['types'])),
                                                                card['id'], card['name'], card['series'])
                                for card in bought),
                        'attachment': 'card.webp'}
            embed['body'] += '\n\nThe card, or a random card from the pack:'
            await ctx.send(embed = await self.bot.embeds.get(embed), file = picture_file)
        else:
            embed = {   'type': 'GENERAL', 'title': 'Unable to buy', 'user': str(ctx.author),
                        'footer': random.choice(constants.FOOTERS), 'color': discord.Color.dark_red(),
                        'body': 'Make sure the name is exactly what appears in the store\n Also you have enough money?'}
            await ctx.send(embed = await self.bot.embeds.get(embed))

    @flags.add_flag("--id", type=str)
    @flags.add_flag("--cost", type=int)
    @flags.add_flag("--amount", type=int)
    @flags.command()
    async def market_sell(self, ctx: commands.Context, **flags):
        """Sell a card
        `market_sell --id swsh1-203 --cost 10000 --amount 2` -> sell 2 swsh1-203 cards for $10000
        `market_sell --amount 1 --cost 1000 --id xy10-14` -> sell 1 xy10-14 for $1000
        """
        
        cost = flags['cost']
        card_id = flags['id']
        amount = flags['amount']
        if not cost and not card_id and not amount:
            return await ctx.send(f"Example: **{ctx.prefix}market_sell --id hgss4-101 --cost 5000 --amount 1**\nThis will put 1 of your hgss4-101 cards at the market costing $5000")
        
        try:
            price = int(cost)
            if price < 0:
                raise ValueError
        except:
            await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'body': "Invalid price", 'title': 'Invalid -- {}'.format(cost),
                        'color': discord.Color.green(), 'footer': 'Requested by {}'.format(str(ctx.author))}))
            return
        try:
            amt = int(amount)
            if amt <= 0:
                raise ValueError
        except:
            await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'body': "Invalid card amount", 'title': 'Invalid -- {}'.format(amount),
                        'color': discord.Color.green(), 'footer': 'Requested by {}'.format(str(ctx.author))}))
            return
        card = await self.bot.db.get_user_card(ctx.author, card_id)
        if card:
            # check if they have enough amount of card
            if card['amount'] - amt < 0:
                embed = {'type': 'GENERAL', 'body': "You don't have enough of the card", 'title': 'Invalid amount -- {}'.format(amt),
                        'color': discord.Color.green(), 'footer': 'Requested by {}'.format(str(ctx.author))}
                await ctx.send(embed = await self.bot.embeds.get(embed))
                return
            if card['amount'] - amt == 0:
                await self.bot.db.remove_card(ctx.author, card['id'])
            else:
                await self.bot.db.decrement_card(ctx.author, card['id'], amount = amt)
            card = await self.bot.db.get_card_info(card['id'])
        else: # not found or you dont have the card
            embed = {'type': 'GENERAL', 'body': "Not found, or you don't have the card", 'title': 'Selling -- {}'.format(card_id),
                        'color': discord.Color.green(), 'footer': 'Requested by {}'.format(str(ctx.author))}
            await ctx.send(embed = await self.bot.embeds.get(embed))
            return
        # add to market
        response = await self.bot.db.add_to_market(ctx.author, price, card['rarity'], card['name'], card['id'], amount)
        if response:
            #added to market
            embed = {'type': 'GENERAL', 'body': "Your card, {}, has been listed to the market".format(card['name']), 'title': 'Added to Market',
                        'color': discord.Color.green(), 'footer': 'Requested by {}'.format(str(ctx.author))}
            await ctx.send(embed = await self.bot.embeds.get(embed))
        else:
            # not added to market -- error
            embed = {'type': 'GENERAL', 'body': "Error adding to market", 'title': 'Error',
                        'color': discord.Color.green(), 'footer': 'Requested by {}'.format(str(ctx.author))}
            await ctx.send(embed = await self.bot.embeds.get(embed))

    async def parse_numerical_flag(self, text):
        if not (1 <= len(text) <= 2):
            return None

        ops = text

        if len(text) == 1 and text[0].isdigit():
            ops = ["=", text[0]]

        elif len(text) == 1 and not text[0][0].isdigit():
            ops = [text[0][0], text[0][1:]]

        if ops[0] not in ("<", "=", ">") or not ops[1].isdigit():
            return None

        return ops

    async def create_filter(self, flags, ctx):
        aggregations = {}
        flatten = lambda t: [item for sublist in t for item in sublist]
        
        for k,v in flags.items():
            if k == 'mine' and flags[k]:
                k = 'owner_id'
                t_val = str(ctx.author.id)
                aggregations[k] = t_val
                continue
            elif k == 'page' or k == 'sort' or k in constants.FILTER_BY_NUMERICAL.keys():
                continue
            if flags[k]:
                inp = ' '.join(flatten(flags[k]))
                if ',' in inp:
                    t_val = inp.split(',')
                    t_val = tuple([x.strip() for x in t_val])
                else:
                    t_val = '%' + inp + '%'
                if k == 'subtype':
                    k = 'sub_type'
                elif k == 'supertype':
                    k = 'super_type'
                elif k == 'evolvesfrom':
                    k = 'evolves_from'
                elif k == 'set':
                    k = 'pc_set'
                elif k == 'type':
                    k = 'types'
                elif k == 'card_id':
                    k = 'pokemon_cards.id'
                elif k == 'market_id':
                    k = 'market.id'
                elif k == 'rarity':
                    k = 'pokemon_cards.rarity'
                aggregations[k] = t_val

        # numerical flags
        for flag, expr in constants.FILTER_BY_NUMERICAL.items():
            if flag in flags:
                for text in flags[flag] or []:
                    ops = await self.parse_numerical_flag(text)

                    if ops is None:
                        raise commands.BadArgument(f"Couldn't parse `--{flag} {' '.join(text)}`")
                    
                    if ops[0] == '<':
                        aggregations[expr] = f"< {int(ops[1])}"
                    elif ops[0] == '=':
                        aggregations[expr] = f"= {int(ops[1])}"
                    elif ops[0] == '>':
                        aggregations[expr] = f"> {int(ops[1])}"
        return aggregations
        
    @flags.add_flag("page", nargs="?", type=int, default=1)
    @flags.add_flag('--sort', action = 'store_true')
    @flags.add_flag("--amount", nargs="+", action="append")
    @flags.add_flag("--hp", nargs="+", action="append")
    @flags.add_flag("--cost", nargs="+", action="append")
    @flags.add_flag("--market_id", nargs="+", action="append")
    @flags.add_flag("--card_id", nargs="+", action="append")
    @flags.add_flag("--name", nargs="+", action="append")
    @flags.add_flag("--rarity", nargs="+", action="append")
    @flags.add_flag("--type", nargs="+", action="append")
    @flags.add_flag("--supertype", nargs="+", action="append")
    @flags.add_flag("--subtype", nargs="+", action="append")
    @flags.add_flag("--artist", nargs="+", action="append")
    @flags.add_flag("--set", nargs="+", action="append")
    @flags.add_flag("--series", nargs="+", action="append")
    @flags.add_flag("--evolvesfrom", nargs="+", action="append")

    # functions
    @flags.add_flag("--remove", type=int)
    @flags.add_flag("--show", type=int)
    @flags.add_flag("--buy", type=int)
    @flags.add_flag("--mine", action="store_true") # to show market listings of user

    @flags.command()
    async def market(self, ctx: commands.Context, **flags):
        """Market functions
        `market 3 --rarity rare --hp > 100 --sort` -> page 3 of rare cards with 100+ hp sorted by cost
        `market --mine` -> first page of user's market listings
        `market --remove <market_id>` -> remove the listing by market_id if it is by the user
        `market --show <market_id>` -> show card art of the listing
        `market --buy <market_id>` -> buy the market listing
        `market --rarity rare --cost < 100` -> show rare listings with cost less than 100
        """
        # Buy a market listing
        if flags['buy']:
            market_id = flags['buy']
            response, output = await self.bot.db.buy_from_market(ctx.author, market_id)
            if response:
                return await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Bought from Market', 'color': discord.Color.blue(),
                                                    'body': output,
                                                    'footer': f'Rich boi {str(ctx.author)}'}))
            else:
                return await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Unable to buy from Market', 'color': discord.Color.red(),
                                                    'body': output,
                                                    'footer': f'Requested by {str(ctx.author)}'}))

        # Remove user's market listing
        if flags['remove']:
            market_id = flags['remove']
            response, card = await self.bot.db.remove_from_market(ctx.author, market_id)
            if response:
                return await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Removed from Market', 'color': discord.Color.blue(),
                                                    'body': f'Removed {market_id} | {card} from market',
                                                    'footer': f'Requested by {str(ctx.author)}'}))                               
            else:
                return await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Unable to remove from Market', 'color': discord.Color.blue(),
                                                    'body': 'Not valid, or not your market listing',
                                                    'footer': f'Requested by {str(ctx.author)}'}))

        # Show card in listing
        if flags['show']:
            market_id = flags['show']
            listing = await self.bot.db.get_market_listing(market_id)
            if listing:
                picture_file = discord.File('data/images/{}.webp'.format(listing['card_id']), filename = 'show.webp')
                embed = {'type': 'GENERAL-ATTACHMENT-IMAGE', 
                            'body': f"{listing['card_name']} | {listing['rarity']} | {listing['card_id']}\n${listing['cost']} | {listing['amount']} cards", 
                            'title': 'Showing Market Listing - {}'.format(listing['id']),
                            'color': discord.Color.green(), 'footer': 'Requested by {}'.format(str(ctx.author)),
                            'attachment': 'show.webp'}
                return await ctx.send(embed = await self.bot.embeds.get(embed), file = picture_file)
            else: # market listing not found
                return await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Unable to show Market listing', 'color': discord.Color.blue(),
                                                    'body': 'Not a valid market listing, make sure market id is correct',
                                                    'footer': f'Requested by {str(ctx.author)}'}))

        if flags['page'] < 1:
            return await ctx.send('Invalid page number')
        aggregations = await self.create_filter(flags, ctx)
        num = await self.bot.db.get_market_count(queries = aggregations)
        if num == 0:
            return await ctx.send('No listings matching this query')

        async def get_page(pidx, clear):
            pgstart = pidx * 20

            listings = await self.bot.db.get_marketV2(pgstart, 20, queries = aggregations, sort = flags['sort'])

            if len(listings) == 0:
                return await ctx.send('No listings in this page')
            
            page = [
                f"`{l['market_id']}` | **${l['cost']}** | {l['rarity']} | {l['card_name']} | {l['card_id']} | {l['amount']}" 
                for l in listings
            ]

            embed = self.bot.Embed(color = discord.Color.dark_teal())
            embed.title = "Market Listings"
            embed.description = '\n'.join(page)[:2048] # limit in embed
            embed.set_footer(text = f"Page {pidx+1} of {math.ceil(num/20)}")
            return embed
        paginator = pagination.Paginator(get_page, num_pages = math.ceil(num / 20))
        await paginator.send(self.bot, ctx, flags['page'] - 1)

def divideList(arr, n): # n is the size to divide by, n = 50 makes teh arr into 50 size arrays in a list
    out = []
    for i in range(0, len(arr), n):
        out.append(arr[i : i + n])
    return out

def setup(bot):
    bot.add_cog(Market(bot))