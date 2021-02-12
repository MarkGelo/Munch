import urllib.request
import os
import json
import pymysql
import time
from pprint import pprint
from dateutil import parser
import shutil
import requests
from os import listdir
from pokemontcgsdk import Card
from pokemontcgsdk import Set
from pokemontcgsdk import Type
from pokemontcgsdk import Supertype
from pokemontcgsdk import Subtype
from PIL import Image
from os import listdir

def read_db_credentials(): # reads rds db credentials from a text file
    creds = {}
    with open('db_credentials.txt', 'r') as f:
        lines = f.readlines()
        creds['rds_host'] = lines[0][:len(lines[0])-1] # remove \n at end
        creds['dbusername'] = lines[1][:len(lines[1])-1]
        creds['password'] = lines[2][:len(lines[2])-1]
        creds['db_name'] = lines[3]
    return creds

creds = read_db_credentials()
# connect to rds
try:
    conn = pymysql.connect(creds['rds_host'], user=creds['dbusername'], passwd=creds['password'], db=creds['db_name'], 
                            connect_timeout=5, charset = 'utf8')
except pymysql.MySQLError as e:
    print('fail to connect')
except:
    print('fail to connect')

def initial_sets_input(): # add sets info on db
    sets = Set.all()
    db = conn.cursor()
    for pc_set in sets:
        name = pc_set.name
        code = pc_set.code
        ptcgo_code = pc_set.ptcgo_code
        series = pc_set.series
        total_cards = pc_set.total_cards # already in int
        standard_legal = str(pc_set.standard_legal)
        expanded_legal = str(pc_set.expanded_legal)
        release_date = parser.parse(pc_set.release_date).date() # only want date, not time
        updated_at = parser.parse(pc_set.updated_at)
        logo_url = pc_set.logo_url
        symbol_url = pc_set.symbol_url
        db.execute('''insert into pokemon_cards_set(    name, code, ptcgo_code, series, total_cards, standard_legal, expanded_legal,
                                                            release_date, updated_at, logo_url, symbol_url)
                                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''', [ name, code, ptcgo_code, series, total_cards, standard_legal,
                                                                                expanded_legal, release_date, updated_at, logo_url, symbol_url])
        conn.commit()

def initial_cards_input_using_sets(sets): # add cards using sets
    db = conn.cursor()
    #sets = Set.all()
    #sets = [x.name for x in sets]
    for pc_set in sets:
        cards = Card.where(set = pc_set)
        for card in cards:
            try:
                pc_id = card.id
                name = card.name
                national_pokedex_number = card.national_pokedex_number
                if card.types: # can be none, error when trying to join
                    types = ','.join(card.types)
                else:
                    types = card.types
                sub_type = card.subtype
                super_type = card.supertype
                if card.hp and card.hp != 'None':
                    hp = int(card.hp)
                else:
                    hp = None
                if card.number:
                    pc_number = card.number
                else:
                    pc_number = None
                artist = card.artist
                rarity = card.rarity
                series = card.series
                pc_set = card.set
                set_code = card.set_code
                if card.retreat_cost: # can be none
                    retreat_cost = ','.join(card.retreat_cost)
                else:
                    retreat_cost = card.retreat_cost
                converted_retreat_cost = card.converted_retreat_cost
                if card.text:
                    pc_text = '\n'.join(card.text)
                else:
                    pc_text = card.text
                if card.attacks:
                    # doesnt necessarily have to have dmg
                    if 'damage' in card.attacks:
                        if 'text' in card.attacks:
                            attacks = '\n'.join(['{}-{}-{}\n{}'.format(','.join(attack['cost']), attack['name'], attack['damage'], attack['text']) for attack in card.attacks])
                        else:
                            attacks = '\n'.join(['{}-{}-{}'.format(','.join(attack['cost']), attack['name'], attack['damage']) for attack in card.attacks])
                    else:
                        if 'text' in card.attacks:
                            attacks = '\n'.join(['{}-{}\n{}'.format(','.join(attack['cost']), attack['name'], attack['text']) for attack in card.attacks])
                        else:
                            attacks = '\n'.join(['{}-{}'.format(','.join(attack['cost']), attack['name']) for attack in card.attacks])
                else:
                    attacks = card.attacks
                if card.weaknesses:
                    weakness = ','.join(['{} {}'.format(weak['type'], weak['value']) for weak in card.weaknesses])
                else:
                    weakness = card.weaknesses
                if card.resistances:
                    resistances = ','.join(['{} {}'.format(resist['type'], resist['value']) for resist in card.resistances])
                else:
                    resistances = card.resistances
                if card.ability:
                    # doesnt necessarily have a type.. how about texT?
                    if 'type' in card.ability:
                        ability = '{} {}\n{}'.format(card.ability['type'], card.ability['name'], card.ability['text']) # only one ability so no need for new line at end
                    else:
                        ability = '{}\n{}'.format(card.ability['name'], card.ability['text'])
                else:
                    ability = card.ability
                if card.ancient_trait:
                    ancient_trait = '{}\n{}'.format(card.ancient_trait['name'], card.ancient_trait['text']) # only one trait so no need for new line at end
                else:
                    ancient_trait = card.ancient_trait
                evolves_from = card.evolves_from
                image_url = card.image_url
                image_url_hi_res = card.image_url_hi_res
                db.execute('''insert into pokemon_cards(    id, name, national_pokedex_number, types, sub_type, super_type, hp, pc_number,
                                                            artist, rarity, series, pc_set, set_code, retreat_cost, converted_retreat_cost,
                                                            pc_text, attacks, weakness, resistances, ability, ancient_trait, evolves_from,
                                                            image_url, image_url_hi_res)
                                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                                                            [   pc_id, name, national_pokedex_number, types, sub_type, super_type, hp, pc_number,
                                                                artist, rarity, series, pc_set, set_code, retreat_cost, converted_retreat_cost,
                                                                pc_text, attacks, weakness, resistances ,ability, ancient_trait, evolves_from,
                                                                image_url, image_url_hi_res])
                conn.commit()
                # download image, check if hi res or not,
                time.sleep(0.5)
                if image_url_hi_res:
                    response = requests.get(image_url_hi_res, stream=True)
                    with open(r'img\{}.png'.format(pc_id), 'wb') as out_file:
                        shutil.copyfileobj(response.raw, out_file)
                    del response
                elif image_url:
                    response = requests.get(image_url, stream=True)
                    with open(r'img\{}.png'.format(pc_id), 'wb') as out_file:
                        shutil.copyfileobj(response.raw, out_file)
                    del response
                else:
                    print('error - {}'.format(pc_id))
            except Exception as e:
                print(e)
                print('ERROR - {}'.format(card.id))
                file1 = open('error.txt', 'a')
                file1.write('{}\n'.format(card.id))
                file1.close()
            except:
                print('error - {}'.format(card.id))

def new_set(set_):
    new_set_ = Set.where(name = set_)
    input_set(new_set_[0])
    cards = Card.where(set = set_)
    for card in cards:
        input_card(card)

def input_set(pc_set):
    db = conn.cursor()
    name = pc_set.name
    code = pc_set.code
    ptcgo_code = pc_set.ptcgo_code
    series = pc_set.series
    total_cards = pc_set.total_cards # already in int
    standard_legal = str(pc_set.standard_legal)
    expanded_legal = str(pc_set.expanded_legal)
    release_date = parser.parse(pc_set.release_date).date() # only want date, not time
    updated_at = parser.parse(pc_set.updated_at)
    logo_url = pc_set.logo_url
    symbol_url = pc_set.symbol_url
    db.execute('''insert into pokemon_cards_set(    name, code, ptcgo_code, series, total_cards, standard_legal, expanded_legal,
                                                        release_date, updated_at, logo_url, symbol_url)
                            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''', [ name, code, ptcgo_code, series, total_cards, standard_legal,
                                                                            expanded_legal, release_date, updated_at, logo_url, symbol_url])
    conn.commit()

def input_card(card): # add card to db
    try:
        db = conn.cursor()
        pc_id = card.id
        name = card.name
        national_pokedex_number = card.national_pokedex_number
        if card.types: # can be none, error when trying to join
            types = ','.join(card.types)
        else:
            types = card.types
        sub_type = card.subtype
        super_type = card.supertype
        if card.hp and card.hp != 'None':
            hp = int(card.hp)
        else:
            hp = None
        if card.number:
            pc_number = card.number
        else:
            pc_number = None
        artist = card.artist
        rarity = card.rarity
        series = card.series
        pc_set = card.set
        set_code = card.set_code
        if card.retreat_cost: # can be none
            retreat_cost = ','.join(card.retreat_cost)
        else:
            retreat_cost = card.retreat_cost
        converted_retreat_cost = card.converted_retreat_cost
        if card.text:
            pc_text = '\n'.join(card.text)
        else:
            pc_text = card.text
        if card.attacks:
            # doesnt necessarily have to have dmg
            if 'damage' in card.attacks:
                if 'text' in card.attacks:
                    attacks = '\n'.join(['{}-{}-{}\n{}'.format(','.join(attack['cost']), attack['name'], attack['damage'], attack['text']) for attack in card.attacks])
                else:
                    attacks = '\n'.join(['{}-{}-{}'.format(','.join(attack['cost']), attack['name'], attack['damage']) for attack in card.attacks])
            else:
                if 'text' in card.attacks:
                    attacks = '\n'.join(['{}-{}\n{}'.format(','.join(attack['cost']), attack['name'], attack['text']) for attack in card.attacks])
                else:
                    attacks = '\n'.join(['{}-{}'.format(','.join(attack['cost']), attack['name']) for attack in card.attacks])
        else:
            attacks = card.attacks
        if card.weaknesses:
            weakness = ','.join(['{} {}'.format(weak['type'], weak['value']) for weak in card.weaknesses])
        else:
            weakness = card.weaknesses
        if card.resistances:
            resistances = ','.join(['{} {}'.format(resist['type'], resist['value']) for resist in card.resistances])
        else:
            resistances = card.resistances
        if card.ability:
            # doesnt necessarily have a type.. how about texT?
            if 'type' in card.ability:
                ability = '{} {}\n{}'.format(card.ability['type'], card.ability['name'], card.ability['text']) # only one ability so no need for new line at end
            else:
                ability = '{}\n{}'.format(card.ability['name'], card.ability['text'])
        else:
            ability = card.ability
        if card.ancient_trait:
            ancient_trait = '{}\n{}'.format(card.ancient_trait['name'], card.ancient_trait['text']) # only one trait so no need for new line at end
        else:
            ancient_trait = card.ancient_trait
        evolves_from = card.evolves_from
        image_url = card.image_url
        image_url_hi_res = card.image_url_hi_res
        db.execute('''insert into pokemon_cards(    id, name, national_pokedex_number, types, sub_type, super_type, hp, pc_number,
                                                    artist, rarity, series, pc_set, set_code, retreat_cost, converted_retreat_cost,
                                                    pc_text, attacks, weakness, resistances, ability, ancient_trait, evolves_from,
                                                    image_url, image_url_hi_res)
                            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                                                    [   pc_id, name, national_pokedex_number, types, sub_type, super_type, hp, pc_number,
                                                        artist, rarity, series, pc_set, set_code, retreat_cost, converted_retreat_cost,
                                                        pc_text, attacks, weakness, resistances ,ability, ancient_trait, evolves_from,
                                                        image_url, image_url_hi_res])
        conn.commit()
        # download image, check if hi res or not,
        time.sleep(0.5)
        if image_url_hi_res:
            response = requests.get(image_url_hi_res, stream=True)
            with open(r'new\{}.png'.format(pc_id), 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
            del response
        elif image_url:
            response = requests.get(image_url, stream=True)
            with open(r'new\{}.png'.format(pc_id), 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
            del response
        else:
            print('error - {}'.format(pc_id))
    except Exception as e:
        print(e)
        print('ERROR - {}'.format(card.id))
        file1 = open('error.txt', 'a')
        file1.write('{}\n'.format(card.id))
        file1.close()
    except:
        print('error - {}'.format(card.id))

def get_all_id(): # get all ids of cards from db
    db = conn.cursor()
    db.execute('select id from pokemon_cards')
    ids = []
    for row in db:
        ids.append(row[0])
    return ids

def get_images(): # get all card id from images -- to make sure got one image for each card
    files = []
    for fileName in listdir('{}\img'.format(os.getcwd())):
        files.append(fileName.replace('.png', ''))
    return files

if __name__ == '__main__':
    #new_set('Darkness Ablaze')
    
    for fileName in listdir('new/'):
        im1 = Image.open('new/{}'.format(fileName))
        im1.save(f"new_webp/{fileName.replace('jpg', 'webp')}")
        im1.close()
    

