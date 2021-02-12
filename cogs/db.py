# for database updates/inserts

import datetime
import random
#from pokemon import STORE, DAILY_MONEY
import pymysql
from discord.ext import commands, flags, tasks
from helpers import constants

DAILY_MONEY = 200 # 200 base daily money, more if event
STORE = [ # 10 cards booster pack, 6 common, 3 uncommon, 1 rare and above, rare+ is 5th from bottom?
    {'name': 'Sword & Shield', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'Sun & Moon', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'XY', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'Black & White', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'HeartGold & SoulSilver', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'Platinum', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'Diamond & Pearl', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'EX', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'E-Card', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'Neo', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'POP', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'Base', 'cost': 900, 'description': 'Booster Pack (10 cards)'},
    {'name': 'Common', 'cost': 50, 'description': 'Random Common card'},
    {'name': 'Uncommon', 'cost': 100, 'description': 'Random Uncommon card'},
    {'name': 'Rare', 'cost': 300, 'description': 'Random Rare card'}
]

# TODO should clean up and merge similar functions together


class Db(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        connection = pymysql.connect(  host = self.bot.config.DB_RDS_HOST, user = self.bot.config.DB_USERNAME,
                                            password = self.bot.config.DB_PASSWORD, database = self.bot.config.DB_NAME, 
                                            connect_timeout = 5, charset = 'utf8')
        self.connection = connection

    async def get_connection(self):
        return self.connection

    async def reconnect(self):
        if not self.connection.open:
            self.connection.ping(reconnect = True)

    async def manual_reconnect():
        conn = True
        resp = ''
        try:
            if not self.connection.open:
                self.connection.ping(reconnect = True) # reconnect db
                resp += 'Reconnected to database\n'
            if not self.connection.open: #check if actually reconnected
                conn = False
                resp += 'Not actually reconnected'
            return conn, 'Still connected to database' if not resp else resp
        except Exception as e:
            conn = False
            resp += 'Error while trying to reconnect - {}'.format(e)
            return conn, resp

    async def get_server_prefix(self, serverID): # gets the server prefix, so servers can setup their own prefix
        try:
            db_cursor = self.connection.cursor()
            db_cursor.execute('select prefix from servers_config where server_id = %s', [serverID])
            out = []
            for row in db_cursor: # should only return 1 row cuz primary key
                out.append(row)
            db_cursor.close()
            return out[0][0]
        except Exception as e:
            return 'p!'

    async def delete_server(self, server_id): # delete server from db
        db_cursor = self.connection.cursor()
        db_cursor.execute('delete from servers_config where server_id = %s', [server_id])
        self.connection.commit()
        db_cursor.execute('delete from servers where server_id = %s', [server_id])
        self.connection.commit()
        db_cursor.close()
        await self.decrement_servers_statistics()

    async def add_server(self, server): # add server to db
        current_date_time = datetime.datetime.now()
        db_cursor = self.connection.cursor()
        db_cursor.execute('''insert into servers(name, server_id, server_owner_name, server_owner_id, region, joined_at) 
                                values(%s,%s,%s,%s,%s,%s)''', [ server.name, str(server.id), str(server.owner),
                                                                str(server.owner_id), str(server.region), current_date_time])
        self.connection.commit()
        db_cursor.execute('insert into servers_config(server_id) values(%s)', [str(server.id)])
        self.connection.commit()
        db_cursor.close()
        await self.increment_servers_statistics()
    
    async def get_server_msgs_per_day(self, server_id):
        cursor = self.connection.cursor()
        cursor.execute('select msgs_per_day from servers where server_id = %s', [server_id])
        msgs = 0
        for row in cursor:
            msgs = row[0]
        return msgs

    async def add_server_interactions_count(self, serverID): # increment total interactions for the server
        db_cursor = self.connection.cursor()
        db_cursor.execute('update servers set total_interactions = total_interactions + 1 where server_id = %s', [serverID])
        self.connection.commit()
        db_cursor.close()

    async def increment_servers_statistics(self):
        db_cursor = self.connection.cursor()
        db_cursor.execute('update statistics set current_servers_total = current_servers_total + 1')
        self.connection.commit()
        db_cursor.close()

    async def decrement_servers_statistics(self):
        db_cursor = self.connection.cursor()
        db_cursor.execute('update statistics set current_servers_total = current_servers_total - 1')
        self.connection.commit()
        db_cursor.close()

    async def get_server_ids(self):
        server_ids = []
        db_cursor = self.connection.cursor()
        db_cursor.execute('select server_id from servers')
        for row in db_cursor:
            server_ids.append(row[0])
        db_cursor.close()
        return server_ids

    async def on_guild_update(self, before, after): # updates database on server info if its updated
        db_cursor = self.connection.cursor()
        if before.id != after.id: # update id
            # update servers_config first because dependant on servers
            db_cursor.execute('update servers_config set server_id = %s where server_id = %s', [after.id, before.id])
            self.connection.commit()
            # update server table
            db_cursor.execute('update servers set server_id = %s where server_id = %s', [after.id, before.id])
            self.connection.commit()
            db_cursor.close()
        if before.name != after.name: # update name of server in table
            db_cursor.execute('update servers set name = %s where server_id = %s', [after.name, after.id])
            self.connection.commit()
            db_cursor.close()
        if before.owner_id != after.owner_id or str(before.owner) != str(after.owner): # update owner id and name
            db_cursor.execute('update servers set server_owner_name = %s, server_owner_id = %s where server_id = %s',
                                [str(after.owner), after.owner_id, after.id])
            self.connection.commit()
            db_cursor.close()
        if before.region != after.region: # update region
            db_cursor.execute('update servers set region = %s where server_id = %s', [str(after.region), after.id])
            self.connection.commit()
            db_cursor.close()

    async def user_name_update(self, new_name, user_id):
        db_cursor = self.connection.cursor()
        db_cursor.execute('update users set name = %s where user_id = %s', [new_name, user_id])
        db_cursor.execute('update servers set server_owner_name = %s where server_owner_id = %s', [new_name, user_id])
        self.connection.commit()
        db_cursor.close()

    async def update_server_prefix(self, serverID, prefix):
        try:
            db_cursor = self.connection.cursor()
            db_cursor.execute('update servers_config set prefix = %s where server_id = %s', [prefix, serverID])
            self.connection.commit()
            db_cursor.close()
            return True
        except Exception as e:
            return False

    async def get_server_channel_id_to_spam(self, serverID): # get channel id to dump cards on -- TODO does it need to be int?, also is it None if no
        try:
            db_cursor = self.connection.cursor()
            db_cursor.execute('select channel_id_to_spam from servers_config where server_id = %s', [serverID])
            out = []
            for row in db_cursor: # should only return 1 row cuz primary key
                out.append(row)
            db_cursor.close()
            return out[0][0]
        except Exception as e:
            return None

    async def update_server_channel_id_to_spam(self, serverID, channelID):
        try:
            db_cursor = self.connection.cursor()
            db_cursor.execute('update servers_config set channel_id_to_spam = %s where server_id = %s', [channelID, serverID])
            self.connection.commit()
            db_cursor.close()
            return True
        except Exception as e:
            return False

    async def get_everyones_collection(self):
        db_cursor = self.connection.cursor()
        db_cursor.execute('''   select card.rarity, sum(users_cards.amount) from pokemon_cards as card
                                    inner join users_cards
                                        on users_cards.pokemon_card_id = card.id
                                group by card.rarity''')
        rarities = {}
        for row in db_cursor:
            if not row[0] or row[0] == 'None':
                if 'None' in rarities:
                    rarities['None'] += row[1]
                else:
                    rarities['None'] = row[1]
            else:
                rarities[row[0]] = row[1]
        db_cursor.execute('''   select card.super_type, sum(users_cards.amount) from pokemon_cards as card
                                    inner join users_cards
                                        on users_cards.pokemon_card_id = card.id
                                group by card.super_type''')
        supertypes = {}
        for row in db_cursor: # no overlap
            supertypes[row[0]] = row[1]
        db_cursor.close()
        stats = await self.get_global_stats()
        total_cards_bot = await self.get_total_cards_bot()
        total_unique = await self.get_unique_total_cards_all()
        percentage = total_unique / total_cards_bot * 100
        return {'rarity': rarities, 'supertype': supertypes, 'total': stats['total_cards'], 'percent': '{:.2f}'.format(percentage)}

    async def get_global_stats(self):
        cursor = self.connection.cursor()
        cursor.execute('select current_cards_total, current_money_total, current_users_total, current_servers_total from statistics')
        stats = {}
        for row in cursor:
            stats['total_cards'] = row[0]
            stats['total_money'] = row[1]
            stats['total_users'] = row[2]
            stats['total_servers'] = row[3]
        cursor.close()
        return stats

    async def get_total_cards_bot(self):
        db_cursor = self.connection.cursor()
        db_cursor.execute('select count(card.id) from pokemon_cards as card')
        for row in db_cursor:
            return row[0]

    async def get_unique_total_cards_all(self):
        db_cursor = self.connection.cursor()
        db_cursor.execute('select count(distinct users.pokemon_card_id) from users_cards as users')
        for row in db_cursor:
            return row[0] # return int of unique cards colelcted by everyone

    async def get_bot_collection(self):
        db_cursor = self.connection.cursor()
        db_cursor.execute('select rarity, count(rarity) from pokemon_cards group by rarity')
        rarity = {}
        for row in db_cursor:
            if not row[0] or row[0] == 'None':
                if 'None' in rarity:
                    rarity['None'] += row[1]
                else:
                    rarity['None'] = row[1]
            else:
                rarity[row[0]] = row[1]
        supertypes = {}
        db_cursor.execute('select super_type, count(super_type) from pokemon_cards group by super_type')
        for row in db_cursor: # no overlap
            supertypes[row[0]] = row[1]
        db_cursor.close()
        total_cards = await self.get_total_cards_bot()
        return rarity, supertypes, total_cards

    async def get_user_stats(self, user_id):
        db_cursor = self.connection.cursor()
        db_cursor.execute('''   select rarity, sum(users_cards.amount) from pokemon_cards
                                    inner join users_cards
                                        where pokemon_cards.id = users_cards.pokemon_card_id and users_cards.user_id = %s 
                                group by rarity''', [user_id])
        rarity = {}
        for row in db_cursor:
            if not row[0] or row[0] == 'None': # if '' or None for rarity, gonna count them together
                if 'None' in rarity:
                    rarity['None'] += row[1]
                else:
                    rarity['None'] = row[1]
            else:
                rarity[row[0]] = row[1]
        db_cursor.close()
        total_cards = await self.get_total_cards_user(user_id)
        total_unique = await self.get_total_unique_cards_user(user_id)
        total_bot = await self.get_total_cards_bot()
        percent = total_unique / total_bot * 100
        return rarity, total_cards, percent

    async def get_total_cards_user(self, user_id):
        db_cursor = self.connection.cursor()
        db_cursor.execute('select sum(users_cards.amount) from users_cards where users_cards.user_id = %s', [user_id])
        for row in db_cursor:
            return row[0]

    async def get_total_unique_cards_user(self, user_id):
        db_cursor = self.connection.cursor()
        db_cursor.execute('select count(users.pokemon_card_id) from users_cards as users where users.user_id = %s', [user_id])
        for row in db_cursor:
            return row[0] # return int of unique cards by user

    async def get_money(self, user):
        db_cursor = self.connection.cursor()
        # get money of user
        db_cursor.execute('select money from users where user_id = %s', [str(user.id)])
        money = None
        for row in db_cursor:
            money = row[0]
        if money is None: # if not in db
            await self.add_user(user)
            return 0
        else:
            return money

    async def add_user(self, user):
        current_date_time = datetime.datetime.now()
        # insert to user table, while also adding 1 to total interactions
        db_cursor = self.connection.cursor()
        # if username not utf-8 - result in no username in db which results in error
        # dont use username anyways so just make user_name = "Nothing" to get rid of errors
        user_name = "Nothing"
        db_cursor.execute('''insert into users(user_id, name, money, total_interactions, joined_at) 
                                values(%s,%s,%s,%s,%s)''', [str(user.id), user_name, 0, 0, current_date_time])
        self.connection.commit()
        db_cursor.close()
        await self.increment_users_statistics() # increment current total users

    async def increment_users_statistics(self):
        db_cursor = self.connection.cursor()
        db_cursor.execute('update statistics set current_users_total = current_users_total + 1')
        self.connection.commit()
        db_cursor.close()

    async def buy(self, user, item):
        # check if in store
        if not any(items['name'] == item for items in STORE):
            return False
        store_item = ''
        for items in STORE:
            if items['name'] == item:
                store_item = items
        money = await self.get_money(user)
        # check if user has enough moeny
        if money - store_item['cost'] < 0:
            # not enough money
            return False
        db_cursor = self.connection.cursor()
        # decrement user money
        db_cursor.execute('update users set money = money - %s where user_id = %s', [store_item['cost'], str(user.id)])
        self.connection.commit()
        # get random cards from db
        if store_item['name'] == 'Rare':
            cards = await self.get_rng_cards(rarity = 'Rare')
        elif store_item['name'] == 'Uncommon':
            cards = await self.get_rng_cards(rarity = 'Uncommon')
        elif store_item['name'] == 'Common':
            cards = await self.get_rng_cards(rarity = 'Common')
        else: # booster pack
            cards = await self.get_rng_cards(series = store_item['name'])
        if not cards: # unable to get cards
            return False
        # add cards to user
        for card in cards:
            await self.add_user_card(user ,card['id'])
        random.shuffle(cards)
        db_cursor.close()
        return cards

    async def get_rng_cards(self, rarity = None, series = None): # used for the store and maybe something else?
        db_cursor = self.connection.cursor()
        if rarity: 
            if rarity == 'Rare':
                db_cursor.execute('''select name, rarity, series, id, types from pokemon_cards
                                        where rarity = 'Rare' and obtainable = 'yes' 
                                    order by rand() limit 1''')
                cards = [] # list of dictionaries
                for row in db_cursor:
                    out = {  'name': row[0], 'rarity': row[1], 'series': row[2],
                                    'id': row[3]}
                    if not row[4]: # if types is null -- non pokemon
                        out['types'] = ''
                    else:
                        out['types'] = row[4].split(',')
                    cards.append(out)
                db_cursor.close()
                return cards
            elif rarity == 'Uncommon':
                db_cursor.execute('''select name, rarity, series, id, types from pokemon_cards
                                        where rarity = 'Uncommon' and obtainable = 'yes' 
                                    order by rand() limit 1''')
                cards = [] # list of dictionaries
                for row in db_cursor:
                    out = {  'name': row[0], 'rarity': row[1], 'series': row[2],
                                    'id': row[3]}
                    if not row[4]: # if types is null -- non pokemon
                        out['types'] = ''
                    else:
                        out['types'] = row[4].split(',')
                    cards.append(out)
                db_cursor.close()
                return cards
            elif rarity == 'Common':
                db_cursor.execute('''select name, rarity, series, id, types from pokemon_cards
                                        where rarity = 'Common' and obtainable = 'yes' 
                                    order by rand() limit 1''')
                cards = [] # list of dictionaries
                for row in db_cursor:
                    out = {  'name': row[0], 'rarity': row[1], 'series': row[2],
                                    'id': row[3]}
                    if not row[4]: # if types is null -- non pokemon
                        out['types'] = ''
                    else:
                        out['types'] = row[4].split(',')
                    cards.append(out)
                db_cursor.close()
                return cards
        if series: # booster pack, 6 common, 3 uncommon, 1 rare+
            cards = []
            # get 6 commons
            db_cursor.execute('''select name, rarity, series, id, types from pokemon_cards
                                    where rarity = 'Common' and series = %s and obtainable = 'yes' 
                                order by rand() limit 6''', [series])
            for row in db_cursor:
                out = {  'name': row[0], 'rarity': row[1], 'series': row[2],
                                'id': row[3]}
                if not row[4]: # if types is null -- non pokemon
                    out['types'] = ''
                else:
                    out['types'] = row[4].split(',')
                cards.append(out)
            # get 3 uncommons
            db_cursor.execute('''select name, rarity, series, id, types from pokemon_cards
                                    where rarity = 'Uncommon' and series = %s and obtainable = 'yes' 
                                order by rand() limit 3''', [series])
            for row in db_cursor:
                out = {  'name': row[0], 'rarity': row[1], 'series': row[2],
                                'id': row[3]}
                if not row[4]: # if types is null -- non pokemon
                    out['types'] = ''
                else:
                    out['types'] = row[4].split(',')
                cards.append(out)
            # get 1 rare+
            db_cursor.execute('''select name, rarity, series, id, types from pokemon_cards
                                    where rarity != 'Uncommon' and rarity != 'Common' and rarity != 'None' and series = %s and obtainable = 'yes' 
                                order by rand() limit 1''', [series])
            for row in db_cursor:
                out = {  'name': row[0], 'rarity': row[1], 'series': row[2],
                                'id': row[3]}
                if not row[4]: # if types is null -- non pokemon
                    out['types'] = ''
                else:
                    out['types'] = row[4].split(',')
                cards.append(out)
            db_cursor.close()
            return cards
        db_cursor.close()
        return False

    async def add_user_card(self, user, card, amount = 1):
        # card is just card_id
        db_cursor = self.connection.cursor()
        user_table = await self.get_row_from_users(str(user.id))
        if user_table: # already in db, so no need to create another user
            # check if user already has this card, if so just increment, if not add
            users_cards = await self.get_row_from_users_cards(str(user.id), card) 
            if users_cards: # user has the card so just increment
                await self.increment_users_card(str(user.id), card, amount = amount)
            else: # user doesnt ahve card so insert
                await self.insert_users_card(str(user.id), card, amount = amount)
            # increment total cards
            await self.increment_card_statistics(amt = amount)
        else: # add to user table
            await self.add_user(user)
            # also add card -- since not in user table, no card at all, so can just directly insert
            await self.insert_users_card(str(user.id), card, amount = amount)
            # increment total cards
            await self.increment_card_statistics(amt = amount)
        db_cursor.close()

    async def get_row_from_users(self, user_id):
        db_cursor = self.connection.cursor()
        db_cursor.execute('select user_id, name, money, total_interactions, joined_at from users where user_id = %s', [user_id])
        out = {}
        for row in db_cursor: # should only return one, cuz primary
            out['user_id'] = row[0]
            out['name'] = row[1]
            out['money'] = int(row[2])
            out['total_interactions'] = int(row[3])
            out['joined_at'] = row[4] # should make to datetime
        db_cursor.close()
        return out

    async def get_row_from_users_cards(self, user_id, card_id):
        db_cursor = self.connection.cursor()
        db_cursor.execute('select user_id, pokemon_card_id, amount from users_cards where user_id = %s and pokemon_card_id = %s', [user_id, card_id])
        out = {}
        for row in db_cursor: # should only return one, cuz primary
            out['user_id'] = row[0]
            out['pokemon_card_id'] = row[1]
            out['amount'] = row[2]
        db_cursor.close()
        return out

    async def increment_card_statistics(self, amt = 1):
        db_cursor = self.connection.cursor()
        db_cursor.execute('''update statistics set current_cards_total = current_cards_total + %s, 
                                                    cards_earned_total = cards_earned_total + %s''', [amt, amt])
        self.connection.commit()
        db_cursor.close()

    async def increment_users_card(self, user_id, card_id, amount = 1):
        db_cursor = self.connection.cursor()
        db_cursor.execute('update users_cards set amount = amount + %s where user_id = %s and pokemon_card_id = %s', [amount, user_id, card_id])
        self.connection.commit()
        db_cursor.close()

    async def get_market(self, query = None):
        cursor = self.connection.cursor()
        if query:
            dic = {'search': '%' + query + '%'}
            cursor.execute('''select id, cost, rarity, card_name, card_id, amount from market 
                                where id like %(search)s or cost like %(search)s 
                                or card_name like %(search)s or card_id like %(search)s or 
                                amount like %(search)s or rarity like %(search)s''', dic)
        else:
            cursor.execute('select id, cost, rarity, card_name, card_id, amount from market')
        cards = []
        for row in cursor:
            cards.append({'market_id': row[0], 'cost': row[1], 'rarity': row[2], 'card_name': row[3], 'card_id': row[4], 'amount': row[5]})
        cursor.close()
        return cards

    async def get_card_info(self, card_id):
        cursor = self.connection.cursor()
        if 'custom' in card_id:
            cursor.execute('select name. id from custom_cards where id = %s', [card_id])
        else:
            cursor.execute('select name, rarity, id from pokemon_cards where id = %s', [card_id])
        card = {}
        for row in cursor:
            card['name'] = row[0]
            card['rarity'] = 'Custom' if 'custom' in card_id else row[1]
            card['id'] = row[2]
        return card

    async def remove_card(self, user, card_id):
        cursor = self.connection.cursor()
        cursor.execute('delete from users_cards where user_id = %s and pokemon_card_id = %s', [str(user.id), card_id])
        self.connection.commit()
        cursor.close()

    async def decrement_card(self, user, card_id, amount = 1):
        cursor = self.connection.cursor()
        cursor.execute('update users_cards set amount = amount - %s where user_id = %s and pokemon_card_id = %s', [amount, str(user.id), card_id])
        self.connection.commit()
        cursor.close()

    async def add_to_market(self, user, price, rarity, card_name, card_id, amount):
        cursor = self.connection.cursor()
        cursor.execute('insert into market(cost,card_name,card_id,amount,owner_id,rarity) values(%s,%s,%s,%s,%s,%s)', 
                                                [price, card_name, card_id, amount,str(user.id),rarity])
        self.connection.commit()
        cursor.close()
        return True

    async def get_market_listing(self, market_id):
        cursor = self.connection.cursor()
        cursor.execute('select id, cost, rarity, card_name, card_id, amount from market where id = %s', [market_id])
        listing = cursor.fetchone()
        if listing is None:
            return None
        out = {'id': listing[0], 'cost': listing[1], 'rarity': listing[2], 'card_name': listing[3],
                'card_id': listing[4], 'amount': listing[5]}
        return out

    async def get_market_listings(self, user, query):
        cursor = self.connection.cursor()
        if query:
            dic = {'user_id': str(user.id), 'search': '%' + query + '%'}
            cursor.execute('''select id, cost, rarity, card_name, card_id, amount from market 
                                where owner_id = %(user_id)s and (
                                id like %(search)s or cost like %(search)s 
                                or card_name like %(search)s or card_id like %(search)s or 
                                amount like %(search)s or rarity like %(search)s)''', dic)
        else:
            cursor.execute(f'select id, cost, rarity, card_name, card_id, amount from market where owner_id = {str(user.id)}')
        cards = []
        for row in cursor:
            cards.append({'market_id': row[0], 'cost': row[1], 'rarity': row[2], 'card_name': row[3], 'card_id': row[4], 'amount': row[5]})
        cursor.close()
        return cards

    async def get_custom_cards(self, user, query = None):
        cursor = self.connection.cursor()
        if query:
            dic = {'user_id': str(user.id), 'search': '%' + query + '%'}
            cursor.execute('''select custom_cards.id, custom_cards.name from custom_cards 
                                    inner join users_cards
                                        on users_cards.pokemon_card_id = custom_cards.id 
                                where users_cards.user_id = %(user_id)s and (
                                custom_cards.id like %(search)s or custom_cards.name like %(search)s''', dic)
        else:
            cursor.execute(f'''select custom_cards.id, custom_cards.name from custom_cards 
                                    inner join users_cards 
                                        on users_cards.pokemon_card_id = custom_cards.id 
                                where users_cards.user_id = {str(user.id)}''')
        cards = []
        for row in cursor:
            cards.append({'id': row[0], 'name': row[1]})
        cursor.close()
        return cards

    async def get_user_sort(self, user):
        cursor = self.connection.cursor()
        cursor.execute('select sort from users where user_id = %s', [str(user.id)])
        for row in cursor:
            return row[0]

    async def update_user_sort(self, user, sort):
        cursor = self.connection.cursor()
        cursor.execute('update users set sort = %s where user_id = %s', [sort, str(user.id)])
        self.connection.commit()
        cursor.close()

    async def get_all_cards(self):
        cursor = self.connection.cursor()
        cursor.execute('''select id, name, national_pokedex_number, types, sub_type,
                            super_type, hp, pc_number, artist, rarity, series, pc_set,
                            set_code, retreat_cost, converted_retreat_cost, pc_text, attacks,
                            weakness, resistances, ability, ancient_trait, evolves_from from pokemon_cards''')
        cards = []
        for row in cursor:
            cards.append({'id': row[0], 'name': row[1], 'national_pokedex_number': row[2],
                            'types': row[3], 'sub_type': row[4], 'super_type': row[5], 'hp': row[6], 'pc_number': row[7],
                            'artist': row[8], 'rarity': row[9], 'series': row[10], 'pc_set': row[11], 'set_code': row[12],
                            'retreat_cost': row[13], 'converted_retreat_cost': row[14], 'pc_text': row[15], 'attacks': row[16],
                            'weakness': row[17], 'resistances': row[18], 'ability': row[19], 'ancient_trait': row[20],
                            'evolves_from': row[21]})
        cursor.close()
        return cards

    async def get_dex(self, user):
        cursor = self.connection.cursor()
        dex = []
        cursor.execute('''select distinct pokemon_card_id from users_cards where user_id = %s''', str(user.id))
        for row in cursor:
            dex.append(row[0])
        cursor.close()
        return dex

    async def get_marketV2(self, skip: int = None, limit: int = None, queries = None, sort = None):
        cursor = self.connection.cursor()
        t_queries = queries.copy()
        if not t_queries:
            cursor.execute('''  select market.id, market.cost, pokemon_cards.rarity, 
                                pokemon_cards.name, market.card_id, market.amount, market.owner_id from market 
                                    inner join pokemon_cards 
                                        on market.card_id = pokemon_cards.id 
                                    ''')
        else:
            stmt = '''  select market.id, market.cost, pokemon_cards.rarity, 
                                pokemon_cards.name, market.card_id, market.amount, market.owner_id from market 
                                    inner join pokemon_cards 
                                        on market.card_id = pokemon_cards.id 
                                    where '''
            i = 0
            for k,v in t_queries.items():
                if i == 0:
                    if k == 'owner_id':
                        stmt += f"{k} = {v} "
                    elif k in constants.FILTER_BY_NUMERICAL.values():
                        stmt += f"{k} {v} "
                    elif isinstance(v, tuple):
                        stmt += f"{k} in %({k})s "
                    else:
                        stmt += f"{k} like %({k})s "
                    i += 1
                else:
                    if k == 'owner_id':
                        stmt += f"and {k} = {v} "
                    elif k in constants.FILTER_BY_NUMERICAL.values():
                        stmt += f"and {k} {v} "
                    elif isinstance(v, tuple):
                        stmt += f"and {k} in %({k})s "
                    else:
                        stmt += f"and {k} like %({k})s "
            cursor.execute(stmt, t_queries)
        listings = []
        for row in cursor:
            listings.append({'market_id': row[0], 'cost': row[1], 'rarity': row[2], 'card_name': row[3], 'card_id': row[4], 'amount': row[5]})
        cursor.close()
        if sort:
            # TODO market sort -- currentlly just sort by cost
            listings = sorted(listings, key = lambda k: k['cost'])
        if skip and limit:
            return listings[skip:limit+skip]
        if skip:
            return listings[skip:]
        if limit:
            return listings[:limit]
        return listings

    async def get_market_count(self, queries = None):
        cursor = self.connection.cursor()
        t_queries = queries.copy()
        if not t_queries:
            cursor.execute('''  select market.id, market.cost, pokemon_cards.rarity, 
                                pokemon_cards.name, market.card_id, market.amount, market.owner_id from market 
                                    inner join pokemon_cards 
                                        on market.card_id = pokemon_cards.id 
                                    ''')
        else:
            stmt = '''  select market.id, market.cost, pokemon_cards.rarity, 
                                pokemon_cards.name, market.card_id, market.amount, market.owner_id from market 
                                    inner join pokemon_cards 
                                        on market.card_id = pokemon_cards.id 
                                    where '''
            i = 0
            for k,v in t_queries.items():
                if i == 0:
                    if k == 'owner_id':
                        stmt += f"{k} = {v} "
                    elif k in constants.FILTER_BY_NUMERICAL.values():
                        stmt += f"{k} {v} "
                    elif isinstance(v, tuple):
                        stmt += f"{k} in %({k})s "
                    else:
                        stmt += f"{k} like %({k})s "
                    i += 1
                else:
                    if k == 'owner_id':
                        stmt += f"and {k} = {v} "
                    elif k in constants.FILTER_BY_NUMERICAL.values():
                        stmt += f"and {k} {v} "
                    elif isinstance(v, tuple):
                        stmt += f"and {k} in %({k})s "
                    else:
                        stmt += f"and {k} like %({k})s "
            cursor.execute(stmt, t_queries)
        listings = []
        for row in cursor:
            listings.append({'market_id': row[0], 'cost': row[1], 'rarity': row[2], 'card_name': row[3], 'card_id': row[4], 'amount': row[5]})
        cursor.close()
        return len(listings)

    async def get_user_cardsV2(self, user_id, skip: int = None, limit: int = None, queries = None, sort = None):
        db_cursor = self.connection.cursor()
        t_queries = queries.copy()
        if not t_queries:
            db_cursor.execute('''   select name, rarity, series, id, users_cards.amount, types from pokemon_cards 
                                        inner join users_cards
                                            on pokemon_cards.id = users_cards.pokemon_card_id
                                        where users_cards.user_id = %s''', [user_id])
        else:
            stmt = """select name, rarity, series, id, users_cards.amount, types from pokemon_cards 
                                        inner join users_cards
                                            on pokemon_cards.id = users_cards.pokemon_card_id
                                        where users_cards.user_id = %(user_id)s """
            stmt += "and ("
            i = 0
            for k,v in t_queries.items():
                if i == 0:
                    if k in constants.FILTER_BY_NUMERICAL.values():
                        stmt += f"{k} {v} "
                    elif isinstance(v, tuple):
                        stmt += f"{k} in %({k})s "
                    else:
                        stmt += f"{k} like %({k})s "
                    i += 1
                else:
                    if k in constants.FILTER_BY_NUMERICAL.values():
                        stmt += f"and {k} {v} "
                    elif isinstance(v, tuple):
                        stmt += f"and {k} in %({k})s "
                    else:
                        stmt += f"and {k} like %({k})s "
            stmt += ")"
            t_queries["user_id"] = user_id
            db_cursor.execute(stmt, t_queries)
        cards = [] # list of dictionaries
        for row in db_cursor:
            out = {  'name': row[0], 'rarity': row[1], 'series': row[2],
                            'id': row[3], 'amount': row[4]}
            if not row[5]: # if types is null -- non pokemon
                out['types'] = ''
            else:
                out['types'] = row[5].split(',')
            cards.append(out)
        db_cursor.close()
        # sort the cards
        if sort:
            cards = await self.sort_list_of_dict(cards, sort)
        if skip and limit:
            return cards[skip:limit+skip]
        if skip:
            return cards[skip:]
        if limit:
            return cards[:limit]
        return cards

    async def sort_list_of_dict(self, dictionary, criteria, skip = None, limit = None):
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

    async def get_user_cards_count(self, user_id, queries = None):
        db_cursor = self.connection.cursor()
        t_queries = queries.copy()
        if not t_queries:
            db_cursor.execute('''   select name, rarity, series, id, users_cards.amount, types from pokemon_cards 
                                        inner join users_cards
                                            on pokemon_cards.id = users_cards.pokemon_card_id
                                        where users_cards.user_id = %s''', [user_id])
        else:
            stmt = """select name, rarity, series, id, users_cards.amount, types from pokemon_cards 
                                        inner join users_cards
                                            on pokemon_cards.id = users_cards.pokemon_card_id
                                        where users_cards.user_id = %(user_id)s """
            stmt += "and ("
            i = 0
            for k,v in t_queries.items():
                if i == 0:
                    if k in constants.FILTER_BY_NUMERICAL.values():
                        stmt += f"{k} {v} "
                    elif isinstance(v, tuple):
                        stmt += f"{k} in %({k})s "
                    else:
                        stmt += f"{k} like %({k})s "
                    i += 1
                else:
                    if k in constants.FILTER_BY_NUMERICAL.values():
                        stmt += f"and {k} {v} "
                    elif isinstance(v, tuple):
                        stmt += f"and {k} in %({k})s "
                    else:
                        stmt += f"and {k} like %({k})s "
            stmt += ")"
            t_queries["user_id"] = user_id
            db_cursor.execute(stmt, t_queries)
        cards = [] # list of dictionaries
        for row in db_cursor:
            out = {  'name': row[0], 'rarity': row[1], 'series': row[2],
                            'id': row[3], 'amount': row[4]}
            if not row[5]: # if types is null -- non pokemon
                out['types'] = ''
            else:
                out['types'] = row[5].split(',')
            cards.append(out)
        db_cursor.close()
        return len(cards)

    async def get_user_cards(self, user_id, query = None):
        db_cursor = self.connection.cursor()
        if not query:
            db_cursor.execute('''   select name, rarity, series, id, users_cards.amount, types from pokemon_cards 
                                        inner join users_cards
                                            on pokemon_cards.id = users_cards.pokemon_card_id
                                        where users_cards.user_id = %s''', [user_id])
        else: # query
            dic = {'user_id': user_id, 'query': "%" + query + "%"}
            db_cursor.execute('''   select name, rarity, series, id, users_cards.amount, types, sub_type,
                                        super_type, artist, pc_text, attacks, ability, ancient_trait 
                                        from pokemon_cards 
                                        inner join users_cards
                                            on pokemon_cards.id = users_cards.pokemon_card_id
                                        where users_cards.user_id = %(user_id)s
                                        and (   name like %(query)s or 
                                                rarity like %(query)s or 
                                                series like %(query)s or 
                                                id like %(query)s or 
                                                types like %(query)s or 
                                                sub_type like %(query)s or 
                                                super_type like %(query)s or 
                                                artist like %(query)s or 
                                                pc_set like %(query)s or 
                                                pc_text like %(query)s or
                                                attacks like %(query)s or 
                                                ability like %(query)s or 
                                                ancient_trait like %(query)s)''', dic)
        cards = [] # list of dictionaries
        for row in db_cursor:
            out = {  'name': row[0], 'rarity': row[1], 'series': row[2],
                            'id': row[3], 'amount': row[4]}
            if not row[5]: # if types is null -- non pokemon
                out['types'] = ''
            else:
                out['types'] = row[5].split(',')
            cards.append(out)
        db_cursor.close()
        return cards

    async def remove_from_market(self, user, market_id):
        cursor = self.connection.cursor()
        cursor.execute('select id, owner_id, card_id, amount, card_name from market where owner_id = %s and id = %s', [str(user.id), market_id])
        market = {}
        for row in cursor:
            market['id'] = row[0]
            market['owner_id'] = row[1]
            market['card_id'] = row[2]
            market['amount'] = row[3]
            market['card_name'] = row[4]
        if not market: # invalid
            return False, 'Not your market listing'
        # remove from market
        cursor.execute('delete from market where owner_id = %s and id = %s', [market['owner_id'], market['id']])
        # add card back to user
        await self.add_user_card(user, market['card_id'], market['amount'])
        self.connection.commit()
        cursor.close()
        return True, market['card_name']
    
    async def buy_from_market(self, user, market_id):
        try:
            cursor = self.connection.cursor()
            cursor.execute('select id, card_id, amount, card_name, cost, owner_id from market where id = %s', [market_id])
            market = {}
            for row in cursor:
                market['id'] = row[0]
                market['card_id'] = row[1]
                market['amount'] = row[2]
                market['card_name'] = row[3]
                market['cost'] = row[4]
                market['owner_id'] = row[5]
            if not market: # invalid
                return False, 'Invalid market_id'
            if market['owner_id'] == str(user.id): #user cant buy his own listing
                return False, 'Cannot buy your own listing'
            money = await self.get_money(user)
            if money - market['cost'] < 0:
                return False, 'Not enough money'
            # decrease buyers money
            cursor.execute('update users set money = money - %s where user_id = %s', [market['cost'], str(user.id)])
            # increase owners money
            cursor.execute('update users set money = money + %s where user_id = %s', [market['cost'], market['owner_id']])
            cursor.execute('delete from market where id = %s', [market['id']])
            await self.add_user_card(user, market['card_id'], market['amount'])
            self.connection.commit()
            cursor.close()
            return True, f"Bought {market['amount']} **{market['card_name']}** for **${market['cost']}**"
        except Exception as e:
            return False, 'Error'

    async def increment_user_interactions(self, userID):
        db_cursor = self.connection.cursor()
        db_cursor.execute('update users set total_interactions = total_interactions + 1 where user_id = %s', [userID])
        self.connection.commit()
        db_cursor.close()

    async def get_support_tickets(self, flags, skip = 0, limit = 0, count = False):
        cursor = self.connection.cursor()
        true_f = [k for k,v in flags.items() if v and k != "show" and k != "page"]
        for k in true_f:
            flags[k] = "%" + k + "%"
        stmt = "SELECT id, user_id, flags, message FROM support "
        stmt = stmt if not true_f else stmt + "WHERE " + 'OR '.join([f"flags like %({k})s" for k in true_f])
        cursor.execute(stmt, flags)
        tickets = []
        for row in cursor:
            tickets.append({"id": row[0], "user_id": row[1], "flags": row[2], "message": row[3]})
        if skip and limit:
            return tickets[skip:limit+skip] if not count else len(tickets[skip:limit])
        elif skip:
            return tickets[skip:] if not count else len(tickets[skip:])
        elif limit:
            return tickets[:limit] if not count else len(tickets[:limit])
        return tickets if not count else len(tickets)

    async def get_daily(self, user, current_time):
        db_cursor = self.connection.cursor()
        db_cursor.execute('select redeemed_at from daily where user_id = %s', [str(user.id)])
        date = ''
        for row in db_cursor:
            date = row[0]
        if not date: # not in table
            # add money and get random card
            await self.add_money(user, DAILY_MONEY)
            card = await self.get_random_card()
            await self.add_user_card(user, card['id'])
            # insert in daily table
            db_cursor.execute('insert into daily(user_id, redeemed_at) values(%s,%s)', [str(user.id), current_time])
            self.connection.commit()
            db_cursor.close()
            return True, card
        else:
            # check if more than 24 hours
            difference = current_time - date
            diff = difference.total_seconds()
            if diff > 3600 * 24: # more than 24 hours
                # add money and get random card
                await self.add_money(user, DAILY_MONEY)
                card = await self.get_random_card()
                await self.add_user_card(user, card['id'])
                # update daily table
                db_cursor.execute('update daily set redeemed_at = %s where user_id = %s', [current_time, str(user.id)])
                self.connection.commit()
                db_cursor.close()
                return True, card
            else:
                db_cursor.close()
                return False, str(datetime.timedelta(seconds = (3600 * 24) - diff))

    async def add_money(self, user, money):
        db_cursor = self.connection.cursor()
        # check if user in db
        db_cursor.execute('select * from users where user_id = %s', [str(user.id)])
        in_db = ''
        for row in db_cursor:
            in_db = row[0]
        if not in_db: # not in db
            # add user
            await self.add_user(user)
        # add money
        db_cursor.execute('update users set money = money + %s where user_id = %s', [money, str(user.id)])
        self.connection.commit()
        # increment money statistics
        db_cursor.execute('update statistics set current_money_total = current_money_total + %s, money_earned_total = money_earned_total + %s', [money, money])
        self.connection.commit()
        db_cursor.close()

    async def subtract_money(self, user, money):
        db_cursor = self.connection.cursor()
        # subtract
        db_cursor.execute('update users set money = money - %s where user_id = %s', [money, str(user.id)])
        self.connection.commit()
        # increment money statistics
        db_cursor.execute('update statistics set current_money_total = current_money_total - %s', [money])
        self.connection.commit()
        db_cursor.close()

    async def random_card(self, type_ = None, rarity = None):
        cursor = self.connection.cursor()
        if type_ and rarity:
            if rarity == 'rare+':
                cursor.execute('''select name, rarity, series, id, types from pokemon_cards 
                                            where types like %s and rarity != 'None' and rarity != 'Common' and rarity != 'Uncommon' 
                                            and rarity != 'Rare' and obtainable = 'yes' 
                                        order by rand() limit 1''', ['%' + type_ + '%'])
                result = cursor.fetchone()
                if result:
                    out = {'name': result[0], 'rarity': result[1], 'series': result[2], 'id': result[3], 'types': result[4]}
                else:
                    raise ValueError('Unable to get 1 random card with rarity and type parameter')
            else:
                cursor.execute('''select name, rarity, series, id, types from pokemon_cards 
                                            where rarity = %s and types like %s and obtainable = 'yes' 
                                        order by rand() limit 1''', [rarity, '%' + type_ + '%'])
                result = cursor.fetchone()
                if result:
                    out = {'name': result[0], 'rarity': result[1], 'series': result[2], 'id': result[3], 'types': result[4]}
                else:
                    raise ValueError('Unable to get 1 random card with rarity and type parameter')
        elif type_:
            cursor.execute('''select name, rarity, series, id, types from pokemon_cards 
                                            where types = %s and obtainable = 'yes' 
                                        order by rand() limit 1''', ['%' + type_ + '%'])
            result = cursor.fetchone()
            if result:
                out = {'name': result[0], 'rarity': result[1], 'series': result[2], 'id': result[3], 'types': result[4]}
            else:
                raise ValueError('Unable to get 1 random card with type parameter')
        elif rarity:
            if rarity == 'rare+':
                cursor.execute('''select name, rarity, series, id, types from pokemon_cards 
                                            where rarity != 'None' and rarity != 'Common' and rarity != 'Uncommon' 
                                            and rarity != 'Rare' and obtainable = 'yes' 
                                        order by rand() limit 1''')
                result = cursor.fetchone()
                if result:
                    out = {'name': result[0], 'rarity': result[1], 'series': result[2], 'id': result[3], 'types': result[4]}
                else:
                    raise ValueError('Unable to get 1 random card with rarity parameter')
            else:
                cursor.execute('''select name, rarity, series, id, types from pokemon_cards
                                            where rarity = %s and obtainable = 'yes' 
                                        order by rand() limit 1''', [rarity])
                result = cursor.fetchone()
                if result:
                    out = {'name': result[0], 'rarity': result[1], 'series': result[2], 'id': result[3], 'types': result[4]}
                else:
                    raise ValueError('Unable to get 1 random card with rarity parameter')
        else:
            cursor.execute("select name, rarity, series, id, types from pokemon_cards where obtainable = 'yes' order by rand() limit 1")
            result = cursor.fetchone()
            if result:
                out = {'name': result[0], 'rarity': result[1], 'series': result[2], 'id': result[3], 'types': result[4]}
            else:
                raise ValueError('Unable to get 1 random card with no parameters')
        cursor.close()
        return out

    async def get_random_card(self): # get random card id -- this function only used by daily and card drops
        db_cursor = self.connection.cursor()
        db_cursor.execute('select id, name, rarity from pokemon_cards where obtainable = %s order by rand() limit 1', ['yes'])
        result = db_cursor.fetchone()
        if result:
            card = {'id': result[0], 'name': result[1], 'rarity': result[2]}
        else:
            raise ValueError('Unable to get 1 random card -- get_random_card()')
        # if rare+ then does it again, so less chance
        # also, if japanese less chance -- don't want 50/50 english, want jap to be less likely
        if card['rarity'] not in ['Common', 'None', 'Rare', 'Uncommon'] or 'jp' in card['id']:
            db_cursor.execute('select id, name, rarity from pokemon_cards where obtainable = %s order by rand() limit 1', ['yes'])
            result = db_cursor.fetchone()
            if result:
                card = {'id': result[0], 'name': result[1], 'rarity': result[2]}
            else:
                raise ValueError('Unable to get 1 random card -- get_random_card()')
        db_cursor.close()
        return card

    async def get_user_card(self, user, card_id):
        db_cursor = self.connection.cursor()
        db_cursor.execute('select pokemon_card_id, amount from users_cards where user_id = %s and pokemon_card_id = %s', [str(user.id), card_id])
        card = {}
        for row in db_cursor: # only one row
            # populate dictionary
            card['id'] = row[0]
            card['amount'] = row[1]
        return card

    async def get_drop(self, channel_id):
        db_cursor = self.connection.cursor()
        db_cursor.execute('select name, id from current_drop where channel_id = %s', [channel_id])
        out = {}
        for row in db_cursor:
            out['name'] = row[0]
            out['id'] = row[1]
        if not out:
            return None
        return out
        
    async def redeem_drop(self, name, channel_id, user): # check if user is correct in redeeming -- also updates db if so
        db_cursor = self.connection.cursor()
        db_cursor.execute('select name, id from current_drop where channel_id = %s', [channel_id])
        out = {}
        for row in db_cursor:
            out['name'] = row[0]
            out['id'] = row[1]
        if not out: # if no current drop
            return 3, None, None
        if name.lower() == out['name'].lower() or name.lower().replace('’', "'") == out['name'].lower().replace('’', "'"): # correct, user redeems card
            db_cursor.execute('delete from current_drop where channel_id = %s', [channel_id])
            self.connection.commit()
            db_cursor.close()
            # add card to user
            await self.add_user_card(user, out['id'])
            return True, out['name'], out['id']
        else: # TODO make this better -- get text differences
            right = out['name'].lower().replace('’', "'")
            answer = name.lower().replace('’', "'")
            diff = zip(right, answer)
            amt = 0
            for i, j in diff:
                if i != j:
                    amt += 1
            length_diff = abs(len(right) - len(answer))
            amt += length_diff
            return False, amt, out['id']

    async def add_server_messages_count(self, serverID): # increment messages count for the server
        db_cursor = self.connection.cursor()
        db_cursor.execute('update servers set messages = messages + 1 where server_id = %s', [serverID])
        self.connection.commit()
        db_cursor.close()

    async def get_server_messages_count(self, server_id):
        db_cursor = self.connection.cursor()
        db_cursor.execute('select messages from servers where server_id = %s', [server_id])
        amt = None
        for row in db_cursor:
            amt = row[0]
        return amt

    async def store_drop(self, card, channelID): # store drop info to db
        # remove last drop from channel if there was one and add current drop
        db_cursor = self.connection.cursor()
        db_cursor.execute('delete from current_drop where channel_id = %s', [channelID])
        self.connection.commit()
        db_cursor.execute('insert into current_drop(id, name, channel_id) values (%s,%s,%s)', [card['id'], card['name'], channelID])
        self.connection.commit()
        db_cursor.close()

    async def is_valid_card(self, card_id):
        try:
            cursor = self.connection.cursor()
            cursor.execute('select id, name, types, rarity, series from pokemon_cards where id = %s', [card_id])
            card = {}
            for row in cursor:
                card['id'] = row[0]
                card['name'] = row[1]
                card['types'] = row[2]
                card['rarity'] = row[3]
                card['series'] = row[4]
            if card and card_id != card['id']:
                return False     
            return card
        except Exception as e:
            return False

    async def give_card_to_user(self, giver, card_id, recipient):
        try:
            db_cursor = self.connection.cursor()
            db_cursor.execute('select amount from users_cards where user_id = %s and pokemon_card_id = %s', [str(giver.id), card_id])
            amount = 0 # card amount
            for row in db_cursor:
                amount = row[0]
            if amount == 0: # unable to give
                return False
            elif amount - 1 == 0: # give but also delete the row from users card because 0 
                db_cursor.execute('update users_cards set amount = amount - 1 where user_id = %s and pokemon_card_id = %s', [str(giver.id), card_id])
                db_cursor.execute('delete from users_cards where user_id = %s and pokemon_card_id = %s', [str(giver.id), card_id])
            else: # give and row stays same just minus 1
                db_cursor.execute('update users_cards set amount = amount - 1 where user_id = %s and pokemon_card_id = %s', [str(giver.id), card_id])
            # check if recipient is a user in db already
            user_table = await self.get_row_from_users(str(recipient.id))
            if user_table: # if user
                # check if user already ahs card
                users_cards = await self.get_row_from_users_cards(recipient.id, card_id)
                if users_cards: # have card, so increment
                    await self.increment_users_card(recipient.id, card_id)
                else: # dont have card, so insert
                    await self.insert_users_card(recipient.id, card_id)
            else: # not user
                await self.add_user(recipient)
                # give card to recipient
                await self.insert_users_card(str(recipient.id), card_id)
            self.connection.commit()
            db_cursor.close()
            return True
        except Exception as e:
            return False

    async def insert_users_card(self, user_id, card_id, amount = 1):
        db_cursor = self.connection.cursor()
        db_cursor.execute('insert into users_cards(user_id, pokemon_card_id, amount) values(%s,%s,%s)', [str(user_id), card_id, amount])
        self.connection.commit()
        db_cursor.close()

    async def give_money(self, giver, amount, receiver):
        try:
            db_cursor = self.connection.cursor()
            # check if giver has enough money
            db_cursor.execute('select money from users where user_id = %s', [str(giver.id)])
            giver_money = 0
            for row in db_cursor:
                giver_money = row[0]
            if giver_money - amount < 0: # not enough money
                return False
            # give money
            db_cursor.execute('update users set money = money - %s where user_id = %s', [amount, str(giver.id)])
            self.connection.commit()
            await self.add_money(receiver, amount)
            db_cursor.close()
            return True
        except Exception as e:
            return False

    async def card_obtainability(self, status, rarity = None, series = None, types = None):
    # status is 'yes' or 'no' for obtainability
    # parameters are in lists so multiple
    # changes cards that satisfy the parameters to the status
        cursor = self.connection.cursor()
        if rarity:
            for rare in rarity:
                cursor.execute('update pokemon_cards set obtainable = %s where rarity = %s', [status, rare])
        if series:
            for ser in series:
                cursor.execute('update pokemon_cards set obtainable = %s where series = %s', [status, ser])
        if types:
            for ty in types:
                cursor.execute('update pokemon_cards set obtainable = %s where types like %s', [status, '%' + ty + '%'])
        self.connection.commit()
        cursor.close()

    async def get_obtainability(self, rarity):
        cursor = self.connection.cursor()
        cursor.execute('select distinct obtainable from pokemon_cards where rarity = %s', [rarity])
        result = cursor.fetchone()
        return result[0]

def setup(bot):
    bot.add_cog(Db(bot))
