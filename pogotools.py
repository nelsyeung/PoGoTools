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

    items = res['responses']['GET_INVENTORY']['inventory_delta'][
        'inventory_items']
    items_pokemon = []

    for item in items:
        item = item['inventory_item_data']

        if 'pokemon_data' in item and 'pokemon_id' in item['pokemon_data']:
            pokemon_data = item['pokemon_data']
            pokemon_id = str(pokemon_data['pokemon_id'])

            items_pokemon.append({
                'id': pokemon_data['id'],
                'name': pokemon[pokemon_id],
                'cp': int(pokemon_data['cp']),
                'iv': get_iv(pokemon_data)
            })

    return items_pokemon


def transfer_pokemon(items_pokemon, config, api):
    """Transfer all Pokemon satisfying the criteria within the config file."""
    logging.info('Transferring all the relevant Pokemon')

    total_transfer = 0

    for p in items_pokemon:
        pokemon_name = p['name'].lower()
        allow_pokemon = config.get('allow', '').lower()
        except_pokemon = config.get('except', '').lower()

        if ((allow_pokemon != 'all' and pokemon_name not in allow_pokemon) or
                pokemon_name in except_pokemon):
            continue

        # Parse user settings for this Pokemon
        below_cp = config['all']['below_cp']
        below_iv = config['all']['below_iv']
        cp_iv_logic = config['all']['cp_iv_logic']

        if config.get(pokemon_name):
            below_cp = config[pokemon_name]['below_cp']
            below_iv = config[pokemon_name]['below_iv']
            cp_iv_logic = config[pokemon_name]['cp_iv_logic']

        # Main transfer logic
        if cp_iv_logic == 'and':
            if p['cp'] >= below_cp or p['iv'] >= below_iv:
                continue
        elif cp_iv_logic == 'or':
            if p['cp'] >= below_cp and p['iv'] >= below_iv:
                continue

        print('Transfer: {:>12}   CP: {:4d}   IV: {:.2f}'.format(
            p['name'], p['cp'], p['iv']))
        time.sleep(0.5)  # Sleep to prevent too many requests
        api.release_pokemon(pokemon_id=p['id'])
        total_transfer += 1

    print('Total transfer: ' + total_transfer)
    logging.info('Transfer complete')


def setup_parser():
    """Return argparse parser."""
    parser = argparse.ArgumentParser(
        description=('Useful Pokemon Go Tools.'),
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-a', '--account', metavar='index', type=int, default=0,
        help='The account index you want to use from the config.json file.\n'
        'For example "-a 0" corresponds to the first account. (default: "0")')

    parser.add_argument(
        '--get-all', action='store_true',
        help='Get all variables stored.')

    parser.add_argument(
        '-p', '--get-pokemon', action='store_true',
        help='List all Pokemon with their CP and IV.')

    parser.add_argument(
        '-s', '--sort-by', choices=['name', 'cp', 'iv'], default='cp',
        help='Sort Pokemon by either their real name, CP or IV. '
        '(default: "CP")')

    parser.add_argument(
        '--hide-cp-below', metavar='CP', type=int, default=0,
        help='Hide pokemon below a certain CP')

    parser.add_argument(
        '--show-cp-below', metavar='CP', type=int, default=9999,
        help='Only show pokemon below a certain CP')

    parser.add_argument(
        '--hide-iv-below', metavar='IV', type=float, default=0.0,
        help='Hide pokemon below a certain IV')

    parser.add_argument(
        '--show-iv-below', metavar='IV', type=float, default=100.0,
        help='Only show pokemon below a certain IV')

    parser.add_argument(
        '--transfer', action='store_true',
        help='Transfer all Pokemon that satisfy the criteria set in your'
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
    api.login(config['auth_service'], config['username'], config['password'])
    logging.info('Logged into %s successfully', config['username'])
    logging.info('Getting user data')
    req = api.create_request()
    req.get_player()
    req.get_inventory()
    res = req.call()

    if args.get_all:
        pprint.pprint(res)

    if args.get_pokemon:
        items_pokemon = sorted(get_pokemon(res), key=lambda k: k[args.sort_by])

        for p in items_pokemon:
            if (p['cp'] >= args.hide_cp_below and
                    p['cp'] <= args.show_cp_below and
                    p['iv'] >= args.hide_iv_below and
                    p['iv'] <= args.show_iv_below):
                print('{:>12}   CP: {:4d}   IV: {:.2f}'.format(
                    p['name'], p['cp'], p['iv']))

        print('Total Pokemon: ' + len(items_pokemon))
        logging.info('Finish listing all Pokemon')

    if args.transfer:
        transfer_pokemon(get_pokemon(res), config['transfer'], api)

if __name__ == '__main__':
    main()
