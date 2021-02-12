# for pokemon functionalities

import discord
from discord.ext import commands, flags, tasks
import datetime
import random
import math
from helpers import pagination, constants, checks
import asyncio

CHANGELOGS = ''
FOOTER = ["Voting gives $400", "Redeem your dailies", "Slowly adding Japanese cards"]

DAILY_MONEY = 200
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


class Pokemon(commands.Cog):
    """Catch em all"""
    def __init__(self, bot):
        self.bot = bot
        self.update_cards.start()
        self.munch_obtainability.start()
        self.get_global_stats.start()
        self.get_bot_collection.start()

    @tasks.loop(minutes = 60.0)
    async def update_cards(self):
        self.cards = await self.bot.db.get_all_cards()

    @tasks.loop(minutes = 60.0)
    async def munch_obtainability(self): # only Rare Rainbow rarities
        obtainability = await self.bot.db.get_obtainability('Rare Rainbow') #
        if obtainability == 'yes':
            await self.bot.db.card_obtainability('no', rarity = ['Rare Rainbow'])
            return
        rng = random.random()
        if rng <= 0.5: # 50% chance
            await self.bot.db.card_obtainability('yes', rarity = ['Rare Rainbow'])

    @tasks.loop(minutes = 30.0)
    async def get_global_stats(self):
        current_date = datetime.datetime.now().date()
        info = await self.bot.db.get_everyones_collection()
        types = ', '.join('**{}**: {}'.format(key, value) for key,value in info['supertype'].items())
        self.global_stats = {'date': current_date, 'info': info, 'types': types}

    @tasks.loop(minutes = 60.0)
    async def get_bot_collection(self):
        current_date = datetime.datetime.now().date()
        rarities, supertypes, total = await self.bot.db.get_bot_collection()
        types = ', '.join('**{}**: {}'.format(key, value) for key,value in supertypes.items())
        self.bot_collection = {'date': current_date, 'types': types, 'rarities': rarities, 
                                'supertypes': supertypes, 'total': total}

    @commands.command(aliases = ['global'])
    async def _global(self, ctx: commands.Context):
        """Show global stats"""

        if self.global_stats is None:
            return
        current_date = self.global_stats['date']
        info = self.global_stats['info']
        types = self.global_stats['types']
        picture_file = discord.File('global.webp', filename = 'global.webp')
        stats_embed = { 'type': 'GENERAL-ATTACHMENT-THUMBNAIL', 'title' : 'Global Statistics', 'color': discord.Color.dark_grey(),
                        'body': '**{}** total cards as of {}:\n**{}%** complete\n\n{}\n'.format(info['total'], current_date, info['percent'], types),
                        'stats':  info['rarity'], 'footer': random.choice(FOOTER),
                        'attachment': 'global.webp'}
        await ctx.send(embed = await self.bot.embeds.get(stats_embed), file = picture_file)
    
    @commands.command(aliases = ['munch.collection'])
    async def munch_collection(self, ctx: commands.Context):
        """Show current bot collection"""

        if self.bot_collection is None:
            return
        current_date = self.bot_collection['date']
        rarities, supertypes, total = self.bot_collection['rarities'], self.bot_collection['supertypes'], self.bot_collection['total']
        types = self.bot_collection['types']
        picture_file = discord.File('back.webp', filename = 'back.webp')
        stats_embed = { 'type': 'GENERAL-ATTACHMENT-THUMBNAIL', 'title' : "Munch's (BOT) Collection", 'footer': random.choice(FOOTER),
                        'body': '**{}** cards as of {}:\n\n{}\n'.format(total, current_date, types), 'stats':  rarities,
                        'color': discord.Color.dark_magenta(), 'attachment': 'back.webp'}
        await ctx.send(embed = await self.bot.embeds.get(stats_embed), file = picture_file)

    @flags.add_flag("page", nargs = "?", type = int, default = 1)
    @flags.add_flag("--set_code", nargs = "+", action = "append")
    @flags.add_flag("--rarity", nargs = "+", action = "append")
    @flags.add_flag("--name", nargs = "+", action = "append")
    @commands.max_concurrency(1, commands.BucketType.user, wait=False)
    @flags.command()
    async def dex(self, ctx: commands.Context, **flags):
        """Show Card Dex
        Available filters - `set_code` `rarity` `name`
        Examples:
        `dex 5 --set_code base1`
        `dex --name Empoleon`"""

        if flags['page'] < 1:
            return await ctx.send("Invalid page number")

        user_dex = await self.bot.db.get_dex(ctx.author)
        dex = self.cards.copy()
        for card in dex:
            if card['id'] in user_dex:
                card['obtained'] = '✅'
            else:
                card['obtained'] = '❌'
        if flags['set_code']:
            dex = [c for c in dex if c['set_code'].lower() in [x.lower() for x in flags['set_code'][0]]]
        if flags['rarity']:
            dex = [c for c in dex if ' '.join(flags['rarity'][0]).lower() in c['rarity'].lower()]
        if flags['name']:
            dex = [c for c in dex if ' '.join(flags['name'][0]).lower() in c['name'].lower()]
        
        if len(dex) == 0:
            return await ctx.send("No cards found with such query")

        dex = [dex[i:i + 20] for i in range(0, len(dex), 20)] # turns into list of lists with 20 elem each

        if flags['page'] > len(dex):
            return await ctx.send(f"Invalid page. Total pages are {len(dex)}")

        page = flags['page'] - 1
        embed = self.bot.Embed(color = 0xF44336)
        embed.title = 'Your Card Dex'
        embed.description = '\n'.join([f'{c["obtained"]} | {c["id"]} | **{c["name"]}** | {c["rarity"]}' for c in dex[page]])[:2048]
        embed.set_footer(text = f"Page {page + 1} out of {len(dex)}")

        msg = await ctx.send(embed = embed)
        await msg.add_reaction("⬅️")
        await msg.add_reaction("➡️")

        def check(reaction, user):
            return reaction.message.id == msg.id and user == ctx.author and (str(reaction.emoji) == '➡️' or str(reaction.emoji) == '⬅️')
        
        try:
            while True:
                reaction, user = await self.bot.wait_for("reaction_add", timeout = 15.0, check = check)
                try:
                    await reaction.remove(user)
                except:
                    pass
                if reaction.emoji == '⬅️':
                    if page > 0:
                        page -= 1
                        embed.description = '\n'.join([f'{c["obtained"]} | {c["id"]} | **{c["name"]}** | {c["rarity"]}' for c in dex[page]])[:2048]
                        embed.set_footer(text = f"Page {page + 1} out of {len(dex)}")
                        await msg.edit(embed = embed)
                elif reaction.emoji == '➡️':
                    if page < len(dex) - 1:
                        page += 1
                        embed.description = '\n'.join([f'{c["obtained"]} | {c["id"]} | **{c["name"]}** | {c["rarity"]}' for c in dex[page]])[:2048]
                        embed.set_footer(text = f"Page {page + 1} out of {len(dex)}")
                        await msg.edit(embed = embed)
        except Exception as e:
            if not e:
                self.bot.log.info(
                f'ERROR (WAIT FOR REACTION) {ctx.command} : {e}'
                )

    @commands.command()
    async def stats(self, ctx: commands.Context):
        """Show user stats"""

        user = ctx.author
        rarity, total, percent = await self.bot.db.get_user_stats(str(user.id))
        money = await self.bot.db.get_money(user)
        stats_embed = { 'type': 'GENERAL-THUMBNAIL', 'title': '{} Cards'.format(str(user)),
                        'footer': random.choice(FOOTER), 'color': discord.Color.dark_orange(),
                        'body': '**{}** cards collected -- **{}%** complete\nMoney: **${}**'.format(total, '{:.2f}'.format(percent), money),
                        'stats':  rarity, 'thumbnail': str(user.avatar_url)}
        await ctx.send(embed = await self.bot.embeds.get(stats_embed))

    @commands.command(aliases=["money"])
    async def balance(self, ctx: commands.Context):
        """Show users money"""
        
        user = ctx.author
        money = await self.bot.db.get_money(user)
        money_embed = { 'type': 'GENERAL-THUMBNAIL', 'title': f'{str(user)} Wallet',
                        'footer': random.choice(FOOTER), 'color': discord.Color.dark_orange(),
                        'body': f"Money: **${money}**", 'thumbnail': str(user.avatar_url)}
        await ctx.send(embed = await self.bot.embeds.get(money_embed))

    @flags.add_flag('--name', action = 'store_true')
    @flags.add_flag('--series', action = 'store_true')
    @flags.add_flag('--id', action = 'store_true')
    @flags.add_flag('--amount', action = 'store_true')
    @flags.add_flag('--rarity', action = 'store_true')
    @flags.command()
    async def sort(self, ctx: commands.Context, **flags):
        """Sort user's card collection
        Available criterias: name, series, id, amount, rarity
        Example `sort --rarity --amount` `sort --id`
        Only max 2 criterias"""

        true_f = [k for k,v in flags.items() if v]
        if len(true_f) == 0:
            return await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'color': discord.Color.dark_teal(),
                                        'title': 'Sorting Help',
                                        'body': f'Can sort name, rarity, series, id, amount\nBut only 2 criteria, Example: `{ctx.prefix}sort --rarity --amount` or `{ctx.prefix}sort --amount`',
                                        'footer': random.choice(FOOTER)}))
        if len(true_f) > 2:
            return await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'color': discord.Color.dark_teal(),
                                        'title': 'Sorting Help',
                                        'body': f'Only two criteras allowed - Ex. `{ctx.prefix}sort --rarity --amount`',
                                        'footer': random.choice(FOOTER)}))

        db_sort = ','.join(true_f)
        await self.bot.db.update_user_sort(ctx.author, db_sort)
        await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'color': discord.Color.dark_teal(),
                                    'title': 'Sorting Updated',
                                    'body': f'Changed collection sorting to {db_sort}',
                                    'footer': random.choice(FOOTER)}))

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
            if k == 'page' or k in constants.FILTER_BY_NUMERICAL.keys():
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
    @flags.add_flag("--amount", nargs="+", action="append")
    @flags.add_flag("--hp", nargs="+", action="append")
    @flags.add_flag("--id", nargs="+", action="append")
    @flags.add_flag("--name", nargs="+", action="append")
    @flags.add_flag("--rarity", nargs="+", action="append")
    @flags.add_flag("--type", nargs="+", action="append")
    @flags.add_flag("--supertype", nargs="+", action="append")
    @flags.add_flag("--subtype", nargs="+", action="append")
    @flags.add_flag("--artist", nargs="+", action="append")
    @flags.add_flag("--set", nargs="+", action="append")
    @flags.add_flag("--series", nargs="+", action="append")
    @flags.add_flag("--evolvesfrom", nargs="+", action="append")
    @flags.command(aliases = ['cards'])
    async def collection(self, ctx: commands.Context, **flags):
        """Show users collection
        Queries: **id|amount|name|rarity|type|supertype|subtype|artist|set|series|evolvesfrom|hp**
        subtype = Item, Stage 1, Supporter, TAG TEAM, etc.
        supertype = Pokemon, Energy, Trainer
        series = Sword & Shield, POP, E-Card, Gym, NEO, etc.
        set = Darkness Ablaze, Rebel Clash, Unified Minds, etc.
        Examples:
        `<prefix>collection 3 --type Psychic --rarity rare, common`
        -> this will show page 3 the user's collection of psychic rares/commons
        `<prefix>collection --artist Ken Sugimori --rarity rare`
        -> show cards with artist ken sugimori with rare rarity
        `<prefix>collection --rarity rare --amount > 2 --hp > 50`
        -> rare cards with at least 2 amount and hp greater than 50
        **jp cards dont have hp information**
        """

        if flags['page'] < 1:
            return await ctx.send('Invalid page number')
        sort = await self.bot.db.get_user_sort(ctx.author)
        
        aggregations = await self.create_filter(flags, ctx)
        # dictionary with filters in em -- key, value = filter, values to filter
        num = await self.bot.db.get_user_cards_count(str(ctx.author.id), queries = aggregations)
        if num == 0:
            return await ctx.send('No cards matching this query')

        async def get_page(pidx, clear):
            pgstart = pidx * 20

            cards = await self.bot.db.get_user_cardsV2(str(ctx.author.id), pgstart, 20, queries = aggregations, sort = sort)

            if len(cards) == 0:
                return await ctx.send('No cards in this page')
            
            page = [
                f"{self.get_rarity_emoji(c['rarity'])}{''.join(self.get_energy_types_emoji(c['types']))} | **{c['id']}** | {c['name']} | **{c['amount']}**" 
                for c in cards
            ]

            embed = self.bot.Embed(color = discord.Color.dark_teal())
            embed.title = "Your cards"
            embed.description = '\n'.join(page)[:2048] # limit in embed
            embed.set_footer(text = f"Page {pidx+1} of {math.ceil(num/20)}")
            return embed
        paginator = pagination.Paginator(get_page, num_pages = math.ceil(num / 20))
        await paginator.send(self.bot, ctx, flags['page'] - 1)

    @commands.command()
    async def daily(self, ctx: commands.Context):
        """Redeem daily reward"""

        now = datetime.datetime.now()
        response, body = await self.bot.db.get_daily(ctx.author, now)
        current_money = await self.bot.db.get_money(ctx.author)
        if response:
            picture_file = discord.File('data/images/{}.webp'.format(body['id']), filename = 'daily.webp')
            embed = {'type': 'GENERAL-ATTACHMENT-IMAGE', 'user': str(ctx.author), 'attachment': 'daily.webp',
                                    'color': discord.Color.gold(), 'title': 'Daily Reward', 'footer': random.choice(FOOTER),
                                    'body': '\n'.join(["Noice, you claimed your dailies.",
                                    f"You got $**{DAILY_MONEY}** and **{body['name']}**",
                                    f"You now have $**{current_money}** monies, u rich boi",
                                    "",
                                    "**[Voting](https://top.gg/bot/717368969102622770/vote) is nice 🙂**",
                                    "*Get $400 for voting*",
                                    "",
                                    f"Here's your sexy card, **{body['id']}**:"])}
            await ctx.send(embed = await self.bot.embeds.get(embed), file = picture_file)
        else:
            await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'color': discord.Color.gold(),
                                    'title': 'Daily Reward', 'footer': random.choice(FOOTER),
                                    'body': 'You have already redeemed ur dailies for today.\nYou can claim in **{}**'.format(body)}))

    @commands.command()
    async def show(self, ctx: commands.Context, card_id):
        """Show a card"""

        card = await self.bot.db.get_user_card(ctx.author ,card_id)
        if card:
            picture_file = discord.File('data/images/{}.webp'.format(card['id']), filename = 'show.webp')
            embed = {'type': 'GENERAL-ATTACHMENT-IMAGE', 'body': '', 'title': 'Showing card -- {}'.format(card['id']),
                        'color': discord.Color.green(), 'footer': random.choice(FOOTER),
                        'attachment': 'show.webp'}
            await ctx.send(embed = await self.bot.embeds.get(embed), file = picture_file)
        else: # not found or you dont have it
            embed = {'type': 'GENERAL', 'body': "Not found, or you don't have the card", 'title': 'Showing card -- {}'.format(card_id),
                        'color': discord.Color.green(), 'footer': random.choice(FOOTER)}
            await ctx.send(embed = await self.bot.embeds.get(embed))

    '''
    @commands.command()
    async def customs(self, ctx: commands.Context, *, query = None): # show list of custom cards of user
        """Show custom cards"""

        page = 1
        if query:
            try:
                if 'page=' in query:
                    spl = query.split('page=')
                    page = int(spl[1])
                    query = spl[0]
                elif 'page =' in query:
                    spl = query.split('page =')
                    page = int(spl[1])
                    query = spl[0]
            except:
                # send page number is not valid
                await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Custom Cards -- Invalid', 'color': discord.Color.dark_teal(),
                                'footer': 'Invalid page number', 'body': 'Invalid page number'}))
                return
        all_cards = await self.bot.db.get_custom_cards(ctx.author, query)
        cards = divideList(all_cards, 15)
        embed = {'type': 'GENERAL', 'title': f'Custom Cards -- {query}' if query else 'Custom Cards', 'color': discord.Color.dark_teal(),
                    'footer': f'Page {page} of {len(cards)}'}
        body = '**ID | NAME**\n\n'
        body += '\n'.join('**{}** | {}'.format(card['id'], card['name']) for card in cards[page - 1]) if len(cards) != 0 and page <= len(cards) and page > 0 else ''
        embed['body'] = body
        await ctx.send(embed = await self.bot.embeds.get(embed))
    '''

    #@commands.max_concurrency(1, commands.BucketType.channel, wait=True)
    @commands.command()
    async def redeem(self, ctx: commands.Context, *, card_name):
        """Redeem a drop"""

        # get last drop from server
        channel_id = await self.bot.db.get_server_channel_id_to_spam(str(ctx.guild.id))
        if str(ctx.channel.id) == channel_id:
            pokemon_name = card_name.replace("\\'", "'")
            response, out, card_id = await self.bot.db.redeem_drop(pokemon_name, str(ctx.channel.id), ctx.author)
            if response == 3: # no current drop in server
                await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Redeeming?',
                                                    'body': 'No current drop in server...',
                                                    'color': discord.Color.greyple(),
                                                    'footer': random.choice(FOOTER)}))
            elif response:
                # correct, got it -- out would be the name of the pokemon
                rng_money = random.randint(1, 5)
                await self.bot.db.add_money(ctx.author, rng_money)
                await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Redeemed',
                                                    'body': '\n'.join([
                                                        f"Successfully redeemed **{out}** - *{card_id}*",
                                                        f"You also found **${rng_money}**",
                                                        "",
                                                        f"{CHANGELOGS}"]),
                                                    'color': discord.Color.greyple(),
                                                    'footer': random.choice(FOOTER)}))
            else: # if false, it would be a tuple, with second element as amt of difference
                # wrong
                await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Redeeming?',
                                                    'body': 'Wrong\nYou are **{}** off'.format(f'{out} letters' if out > 1 else f'{out} letter'),
                                                    'color': discord.Color.greyple(),
                                                    'footer': random.choice(FOOTER)}))
        else:
            return # not same channel so dont do anything

    @commands.cooldown(1, 20, commands.BucketType.channel)
    @commands.command(aliases=["h"])
    async def hint(self, ctx: commands.Context):
        """Hint for name of the current drop"""
        
        current_drop = await self.bot.db.get_drop(str(ctx.channel.id))
        if current_drop is None:
            return await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Hint',
                                                    'body': f"No drop",
                                                    'color': discord.Color.greyple(),
                                                    'footer': random.choice(FOOTER)}))
        inds = [i for i, x in enumerate(current_drop['name']) if x.isalpha()]
        blanks = random.sample(inds, len(inds) // 2)
        hint = " ".join(
            "".join(x if i in blanks else "\\_" for i, x in enumerate(x))
            for x in current_drop['name'].split()
        )

        await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'title': 'Hint',
                                                    'body': f"The card name is {hint}",
                                                    'color': discord.Color.greyple(),
                                                    'footer': random.choice(FOOTER)}))

    async def card_drop(self, serverID): # card drop for a channel if there is one
        channel_id = await self.bot.db.get_server_channel_id_to_spam(serverID)
        if not channel_id:
            return
        card = await self.bot.db.get_random_card()
        prefix = await self.bot.db.get_server_prefix(serverID)
        await self.bot.db.store_drop(card, channel_id) # store current drop in db
        picture_file = discord.File('data/images/{}.webp'.format(card['id']), filename = 'card.webp')
        channel = self.bot.get_channel(int(channel_id))
        # TODO bot may not be able to get channel cuz of permission or whatever
        # should return something? but where to send? or just log it?
        if channel:
            await channel.send(file = picture_file, 
                                embed = await self.bot.embeds.get({'type': 'GENERAL-ATTACHMENT-IMAGE', 'title': 'Pokemon Card Drop',
                                                    'body': f'A card dropped!\nType `{prefix}redeem <name>` to redeem\nDo `{prefix}hint` for help',
                                                    'color': discord.Color.light_grey(),
                                                    'footer': random.choice(FOOTER),
                                                    'attachment': 'card.webp'}))
        else: # bot couldnt get channel
            pass

    @commands.command()
    async def give(self, ctx: commands.Context, recipient: discord.Member, item):
        """Give a user a card"""
        
        # orange color
        giver = ctx.author
        if recipient is None:
            await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'color': discord.Color.orange(), 
                    'title': 'Nice guy? :point_right: {}'.format(str(giver)),
                    'body': 'Unable to give {} to {} :(\n**Reason**: Not a valid user? or not in server?'.format(item, recipient), 
                    'footer': random.choice(FOOTER)}))
            return
        if is_int(item): # giving money
            amount = int(item)
            if amount < 0: # negative money
                embed = {   'type': 'GENERAL', 'color': discord.Color.orange(), 'footer': random.choice(FOOTER),
                            'title': 'Negative money', 
                            'body': "bro, {} ...".format(amount)}
                await ctx.send(embed = await self.bot.embeds.get(embed))
                return
            response = await self.bot.db.give_money(giver, amount, recipient)
            if response:
                embed = {   'type': 'GENERAL', 'color': discord.Color.orange(), 'footer': random.choice(FOOTER),
                            'title': 'Giving money to the poor?', 'body': 'Gave **${}** to {}'.format(amount, str(recipient))}
                await ctx.send(embed = await self.bot.embeds.get(embed))
            else:
                embed = {   'type': 'GENERAL', 'color': discord.Color.orange(), 'footer': random.choice(FOOTER),
                            'title': 'Unable to give money cuz you poor?', 'body': "{}... bud, you don't have **${}**".format(str(giver), amount)}
                await ctx.send(embed = await self.bot.embeds.get(embed))
        else: # giving card
            card = await self.bot.db.is_valid_card(item)
            if not card: # not valid card
                await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'color': discord.Color.orange(), 
                    'title': 'Nice guy? :point_right: {}'.format(str(giver)),
                    'body': 'Unable to give {} to {} :(\n**Reason**: Not a valid card?'.format(item, str(recipient)), 
                    'footer': random.choice(FOOTER)}))  
                return
            given = await self.bot.db.give_card_to_user(giver, card['id'],  recipient)
            if given:
                await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'footer': random.choice(FOOTER),
                'body': 'Gave **{}** to {} :)'.format(card['name'], str(recipient)), 'title': 'Nice guy? :point_right: {}'.format(str(giver)),
                'color': discord.Color.orange()}))
            else: # not successfully given
                await ctx.send(embed = await self.bot.embeds.get({'type': 'GENERAL', 'footer': random.choice(FOOTER), 
                'body': "Unable to give **{}** to {} :(\n**Reason**: You don't have the card?".format(card['name'], str(recipient)), 
                'color': discord.Color.orange(), 'title': 'Nice guy? :point_right: {}'.format(str(giver))}))
        
    def get_rarity_emoji(self, text): # get emoji for corresponding rarities
        if text == 'None':
            return emojis['NONE']
        elif text == 'Common':
            return emojis['COMMON']
        elif text == 'Uncommon':
            return emojis['UNCOMMON']
        elif text == 'Rare':
            return emojis['RARE']
        else:
            return emojis['RARER']

    def get_energy_types_emoji(self, text):
        types = []
        for energy in text:
            types.append(emojis[energy.upper()])
        if not types: # if no type
            return [emojis['NONE']]
        return types

async def sort_list_of_dict(dictionary, criteria, skip = None, limit = None):
    # amount,rarity -> amount takes precedence, then sorts by rarity
    # rarity,amount -> rarity has precedence
    criteria = criteria.replace('rarity', 'rarityN').replace('amount', 'amountN').replace('series', 'seriesN')
    crit = criteria.split(',')
    # series should have recent be first
    series = {'Sword & Shield': 1, 'Sun & Moon': 2, 'XY': 3, 'Black & White': 4, 'HeartGold & SoulSilver': 5,
                'Platinum': 6, 'POP': 7,'Diamond & Pearl': 8, 'EX': 9, 'E-Card': 10, 'Neo': 11,
                'Gym': 12, 'Base': 13, 'IDK': 999}
    # rarity should have the most rare be first
    rarity = {'LEGEND': 1, 'Rare Rainbow': 2, 'VM': 3, 'V': 5, 'Shining': 6,
                'Amazing Rare': 7, 'BREAK': 10,
                'Rare Secret': 11, 'GX': 12, 'EX': 13, 'Rare Ultra': 14,
                'Rare Holo': 15, 'Rare': 16, 'Uncommon': 17, 'Common': 18, 'None': 19}
    dictionary = [dict(item, **{'rarityN': rarity[item['rarity']]}) for item in dictionary] if 'rarityN' in criteria else dictionary
    dictionary = [dict(item, **{'seriesN': series[item['series']] if item['series'] in series else series['IDK']}) for item in dictionary] if 'seriesN' in criteria else dictionary
    dictionary = [dict(item, **{'amountN': item['amount'] * (-1)}) for item in dictionary] if 'amountN' in criteria else dictionary
    if len(crit) == 2:
        out = sorted(dictionary, key = lambda i: (i[crit[0]], i[crit[1]]))
    elif len(crit) == 1:
        out = sorted(dictionary, key = lambda i: i[crit[0]])
    else:
        out = sorted(dictionary, key = lambda i: i['amount'], reverse = True)
    if skip and limit:
        return out[skip:limit+skip]
    elif skip:
        return out[skip:]
    elif limit:
        return out[:limit]
    else:
        return out

def divideList(arr, n): # n is the size to divide by, n = 50 makes teh arr into 50 size arrays in a list
    out = []
    for i in range(0, len(arr), n):
        out.append(arr[i : i + n])
    return out

def is_int(s):
    try:
        int(s)
        return True
    except:
        return False

def setup(bot):
    bot.add_cog(Pokemon(bot))