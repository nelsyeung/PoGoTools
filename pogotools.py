#!/usr/bin/env python
import os
import argparse
import json
import pprint
import pgoapi


def get_iv(pokemon):
    """Calculate Pokemon IV percentage."""
    return ((pokemon.get('individual_attack', 0) +
             pokemon.get('individual_stamina', 0) + pokemon.get(
                 'individual_defense', 0) + 0.0) / 45.0) * 100.0


def get_pokemon(args, res):
    """List all Pokemon with their CP and IV."""
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
                'name': pokemon[pokemon_id],
                'cp': int(pokemon_data['cp']),
                'iv': get_iv(pokemon_data)
            })

    items_pokemon = sorted(items_pokemon, key=lambda k: k[args.sort_by])

    for p in items_pokemon:
        if (p['cp'] >= args.hide_cp_below and
                p['cp'] <= args.show_cp_below and
                p['iv'] >= args.hide_iv_below and
                p['iv'] <= args.show_iv_below):
            print('{:>12}   CP: {:4d}   IV: {:.2f}'.format(
                p['name'], p['cp'], p['iv']))


def parser():
    """Return parsed command line arguments."""
    parser = argparse.ArgumentParser(
        description=('Useful Pokemon Go Tools.'),
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-a', '--account', type=int, default=0,
        help='The account index you want to use from the config.json file.\n'
        'For example "-a 0" corresponds to the first account. (Default: "0")')

    parser.add_argument(
        '--get-all', action='store_true',
        help='Get all variables stored.')

    parser.add_argument(
        '-p', '--get-pokemon', action='store_true',
        help='List all Pokemon with their CP and IV.')

    parser.add_argument(
        '-s', '--sort-by', choices=['name', 'cp', 'iv'], default='cp',
        help='Sort Pokemon by either their real name, CP or IV. '
        '(default "CP")')

    parser.add_argument(
        '--hide-cp-below', type=int, default=0,
        help='Hide pokemon below a certain CP')

    parser.add_argument(
        '--show-cp-below', type=int, default=9999,
        help='Only show pokemon below a certain CP')

    parser.add_argument(
        '--hide-iv-below', type=float, default=0.0,
        help='Hide pokemon below a certain IV')

    parser.add_argument(
        '--show-iv-below', type=float, default=100.0,
        help='Only show pokemon below a certain IV')

    return parser.parse_args()


def main():
    args = parser()

    # Read user config file
    with open('config.json', 'r') as f:
        config = json.load(f)['accounts'][args.account]

    api = pgoapi.PGoApi()
    api.set_position(config['latitude'], config['longitude'], 0.0)
    api.login(config['auth_service'], config['username'], config['password'])
    req = api.create_request()
    req.get_player()
    req.get_inventory()
    res = req.call()

    if args.get_all:
        pprint.pprint(res)

    if args.get_pokemon:
        get_pokemon(args, res)

if __name__ == '__main__':
    main()
