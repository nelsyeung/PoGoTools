#!/usr/bin/env python
import sys
import os
import argparse
import json
import pprint
import logging
import time
import geopy
import pgoapi
import datetime


def print_total(num_chars, field, total):
    """Print total number of specified field centred with the number of chars
    above and add dashes if there actually has been some listing above."""
    print_str = '{:^' + str(num_chars) + '}'

    # Only print dashes if there has been some listing above
    if total > 0:
        dashes = ''

        for _ in range(num_chars):
            dashes += '-'

        print(print_str.format(dashes))

    print(print_str.format(
        'Total ' + field + ': ' + str(total)))


def get_iv(pokemon):
    """Calculate Pokemon IV percentage."""
    return ((pokemon.get('individual_attack', 0) +
             pokemon.get('individual_stamina', 0) + pokemon.get(
                 'individual_defense', 0) + 0.0) / 45.0) * 100.0


def get_pokemon(res):
    """Get all Pokemon with their CP and IV."""
    logging.info('Getting a list of all your Pokemon')

    # Read Pokemon names from file
    pokemon_file = os.path.join('data', 'pokemon.json')
    with open(pokemon_file, 'r') as f:
        pokemon = json.load(f)

    inventory = res['responses']['GET_INVENTORY']['inventory_delta'][
        'inventory_items']
    inventory_pokemon = []

    for item in inventory:
        item = item['inventory_item_data']

        if 'pokemon_data' in item and 'pokemon_id' in item['pokemon_data']:
            pokemon_data = item['pokemon_data']

            inventory_pokemon.append({
                'id': pokemon_data['id'],
                'name': pokemon[str(pokemon_data['pokemon_id'])],
                'cp': int(pokemon_data['cp']),
                'attack': pokemon_data.get('individual_attack', 0),
                'defense': pokemon_data.get('individual_defense', 0),
                'stamina': pokemon_data.get('individual_stamina', 0),
                'iv': get_iv(pokemon_data),
                'time': pokemon_data.get('creation_time_ms', 0)
            })

    return inventory_pokemon


def transfer_pokemon(inventory_pokemon, config, api):
    """Transfer all Pokemon satisfying the criteria within the config file."""
    logging.info('Transferring all the relevant Pokemon')

    total_transfer = 0

    for p in inventory_pokemon:
        pokemon_name = p['name'].lower()
        allow_pokemon = config.get('allow', '').lower()
        except_pokemon = config.get('except', '').lower()

        if ((allow_pokemon != 'all' and pokemon_name not in allow_pokemon) or
                pokemon_name in except_pokemon):
            continue

        # Parse user settings for this Pokemon
        below_cp = config['all']['below_cp']
        below_iv = config['all']['below_iv']
        logic = config['all']['logic']

        if config.get(pokemon_name):
            below_cp = config[pokemon_name]['below_cp']
            below_iv = config[pokemon_name]['below_iv']
            logic = config[pokemon_name]['logic']

        # Main transfer logic
        if logic == 'and':
            if p['cp'] >= below_cp or p['iv'] >= below_iv:
                continue
        elif logic == 'or':
            if p['cp'] >= below_cp and p['iv'] >= below_iv:
                continue

        print('Transfer: {:>12}   CP: {:4d}   IV: {:.2f}'.format(
            p['name'], p['cp'], p['iv']))

        time.sleep(0.5)  # Sleep to prevent too many requests
        api.release_pokemon(pokemon_id=p['id'])
        total_transfer += 1

    print_total(46, 'transfer', total_transfer)
    logging.info('Transfer complete')


def get_items(res):
    """Return all items excluding Pokemon and eggs."""
    logging.info('Getting a list of all your items')

    # Read item names from file
    items_file = os.path.join('data', 'items.json')
    with open(items_file, 'r') as f:
        items = json.load(f)

    inventory = res['responses']['GET_INVENTORY']['inventory_delta'][
        'inventory_items']
    inventory_items = []

    for item in inventory:
        item = item['inventory_item_data']

        if 'item' in item and 'count' in item['item']:
            item_data = item['item']

            inventory_items.append({
                'id': item_data['item_id'],
                'name': items[str(item_data['item_id'])],
                'count': item_data['count']
            })

    return inventory_items


def recycle_items(inventory_items, config, api):
    """Recycle all items satisfying the criteria within the config file."""
    logging.info('Transferring all the relevant items')

    total_recycle = 0

    for item in inventory_items:
        config_item = config.get(item['name'].lower())

        if config_item and item['count'] > config_item['above_count']:
            recycle_count = item['count'] - config_item['above_count']

            print('Recycle: {:>24}  {:<3d}'.format(
                item['name'], recycle_count))

            time.sleep(0.5)  # Sleep to prevent too many requests
            api.recycle_inventory_item(item_id=item['id'], count=recycle_count)
            total_recycle += recycle_count

    print_total(39, 'recycle', total_recycle)
    logging.info('Transfer complete')


def evolve_pokemon(inventory_pokemon, config, api):
    """Evolve all Pokemon satisfying the criteria within the config file."""
    logging.info('Evolving all the relevant Pokemon')

    total_evolve = 0

    for p in inventory_pokemon:
        pokemon_name = p['name'].lower()
        allow_pokemon = config.get('allow', '').lower()
        except_pokemon = config.get('except', '').lower()

        if ((allow_pokemon != 'all' and pokemon_name not in allow_pokemon) or
                pokemon_name in except_pokemon):
            continue

        # Parse user settings for this Pokemon
        above_cp = config['all']['above_cp']
        above_iv = config['all']['above_iv']
        logic = config['all']['logic']

        if config.get(pokemon_name):
            above_cp = config[pokemon_name]['above_cp']
            above_iv = config[pokemon_name]['above_iv']
            logic = config[pokemon_name]['logic']

        # Main evolve logic
        if logic == 'and':
            if p['cp'] < above_cp or p['iv'] < above_iv:
                continue
        elif logic == 'or':
            if p['cp'] < above_cp and p['iv'] < above_iv:
                continue

        print('Evolve: {:>12}   CP: {:4d}   IV: {:2.0f}%'.format(
            p['name'], p['cp'], p['iv'])),

        time.sleep(0.5)  # Sleep to prevent too many requests

        if (api.evolve_pokemon(pokemon_id=p['id'])
                ['responses']['EVOLVE_POKEMON'].get('experience_awarded')):
            print('- Success')
            total_evolve += 1
        else:
            print('- Failed')

    print_total(51, 'evolve', total_evolve)
    logging.info('Evolve complete')


def setup_parser():
    """Return argparse parser."""
    parser = argparse.ArgumentParser(
        description=('Useful Pokemon Go Tools.'),
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-a', '--account', metavar='index', type=int, default=0,
        help='The account index you want to use from the config.json file.\n'
             'For example "-a 0" corresponds to the first account. '
             '(default: 0)')

    parser.add_argument(
        '--get-all', action='store_true',
        help='Get all variables stored.')

    parser.add_argument(
        '-p', '--get-pokemon', action='store_true',
        help='List all Pokemon with their CP and IV.')

    parser.add_argument(
        '-s', '--sort-by', choices=['name', 'cp', 'iv', 'time'],
        help='Sort Pokemon by either their real name, CP or IV. '
             '(default: name)')

    parser.add_argument(
        '--hide-pokemon', metavar='name', default='',
        help='Hide specified Pokemon separated by comma\n'
             'Example: --hide-pokemon pidgey,weedle,rattata')

    parser.add_argument(
        '--show-pokemon', metavar='name', default='',
        help='Show only the specified Pokemon separated by comma\n'
             'Example: --show-pokemon pidgey,weedle,rattata')

    parser.add_argument(
        '--hide-cp-below', metavar='CP', type=int, default=0,
        help='Hide Pokemon below a certain CP')

    parser.add_argument(
        '--show-cp-below', metavar='CP', type=int, default=9999,
        help='Only show Pokemon below a certain CP')

    parser.add_argument(
        '--hide-iv-below', metavar='IV', type=float, default=0.0,
        help='Hide Pokemon below a certain IV')

    parser.add_argument(
        '--show-iv-below', metavar='IV', type=float, default=100.0,
        help='Only show Pokemon below a certain IV')

    parser.add_argument(
        '--transfer', action='store_true',
        help='Transfer all Pokemon that satisfy the criteria set in your'
             'config file')

    parser.add_argument(
        '-i', '--get-items', action='store_true',
        help='List all items excluding Pokemon and eggs.')

    parser.add_argument(
        '--recycle', action='store_true',
        help='Transfer all items that satisfy the criteria set in your'
             'config file')

    parser.add_argument(
        '--evolve', action='store_true',
        help='Evolve all Pokemon that satisfy the criteria set in your'
             'config file')

    return parser


def main():
    parser = setup_parser()

    # Print help message and exit if no arguments are passed in
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('pgoapi').setLevel(logging.WARNING)

    # Read user config file
    with open('config.json', 'r') as f:
        config = json.load(f)['accounts'][args.account]

    # Check if location is latitude and longitude, or a name
    location = config['location'].split(',')
    if len(location) == 2:
        try:
            latitude = float(location[0])
            longitude = float(location[1])
            logging.info('Location supplied is already in latitude and'
                         'longitude form')
        except ValueError:
            logging.info('Getting the longitude and latitude for %s',
                         config['location'])
            geolocator = geopy.geocoders.Nominatim()
            location = geolocator.geocode(config['location'])
            latitude = location.latitude
            longitude = location.longitude

    api = pgoapi.PGoApi()
    logging.info('Setting the position to %f, %f', latitude, longitude)
    api.set_position(latitude, longitude, 0.0)

    logging.info('Logging into %s', config['username'])
    if not api.login(config['auth_service'],
                     config['username'],
                     config['password']):
        logging.error('Login unsuccessful')
        logging.error('Perhaps Niantic server is down')
        sys.exit(1)
    logging.info('Logged into %s successfully', config['username'])

    logging.info('Getting user data')
    for i in range(1, 11):
        try:
            req = api.create_request()
            req.get_player()
            req.get_inventory()
            res = req.call()
            break
        except:
            wait_time = 0.2
            logging.error('Cannot get user data (trial: %d/10)', i)

            if i == 10:
                logging.error('Please wait a moment then try again')
                sys.exit(1)

            logging.error('Trying again in %.1fs', wait_time)
            time.sleep(wait_time)

    if args.get_all:
        pprint.pprint(res)

    if args.get_pokemon:
        sort_by = 'name'
        listed_pokemon = 0

        # Override default sort with config then argument
        if not args.sort_by:
            if (config.get('get_pokemon') and
                    config['get_pokemon'].get('sort_by')):
                sort_by = config['get_pokemon']['sort_by']
        else:
            sort_by = args.sort_by

        inventory_pokemon = sorted(get_pokemon(res),
                                   key=lambda k: k[sort_by])

        for p in inventory_pokemon:
            if p['name'].lower() in args.hide_pokemon:
                continue

            if (args.show_pokemon and
                    p['name'].lower() not in args.show_pokemon):
                continue

            if (p['cp'] >= args.hide_cp_below and
                    p['cp'] <= args.show_cp_below and
                    p['iv'] >= args.hide_iv_below and
                    p['iv'] <= args.show_iv_below):
                listed_pokemon += 1
                print('{:>12}   CP: {:4d}   IV [A/D/S]: '
                      '[{:02d}/{:02d}/{:02d}] {:2.0f}%   '
                      'Captured: {:%Y-%m-%d %H:%M:%S}'.format(
                        p['name'], p['cp'], p['attack'], p['defense'],
                        p['stamina'], p['iv'],
                        datetime.datetime.fromtimestamp(p['time'] / 1000.0)))

        print_total(84, 'listed Pokemon', listed_pokemon)
        print_total(84, 'Pokemon', len(inventory_pokemon))
        logging.info('Finish listing all your Pokemon')

    if args.transfer:
        transfer_pokemon(get_pokemon(res), config['transfer'], api)

    if args.get_items:
        total_items = 0

        for item in get_items(res):
            total_items += item['count']
            print('{:>24}  {:<3d}'.format(item['name'], item['count']))

        print_total(30, 'items', total_items)
        logging.info('Finish listing all your items')

    if args.recycle:
        recycle_items(get_items(res), config['recycle'], api)

    if args.evolve:
        evolve_pokemon(get_pokemon(res), config['evolve'], api)

if __name__ == '__main__':
    main()
