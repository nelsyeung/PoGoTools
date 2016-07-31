# PoGoTools

Some useful Pokemon Go CLI tools. This is going to be strictly a set of *single run* tools only,
i.e., it won't keep the user logged in.

## Features
- List all Pokemon with their CP and IV.
- Sort the listed Pokemon by their real name, CP or IV.
- Filter the list of Pokemon to a certain CP and IV.
- Transfer Pokemon based on your own criteria

## Installation
You need to have `Python` and `pip` installed on your computer. Please refer to other online
documentations on how to install them on your computer. It is recommended that you use `virtualenv`
with this, so that it won't cluster up your computer with Python packages.

1. Download this project either with `git` or simply download the zip file then unzip it:
	```sh
	git clone https://github.com/nelsyeung/PoGoTools.git
	```

2. Open up terminal and change to the downloaded folder:
	```sh
	cd PoGoTools
	```

3. Install the necessary Python packages by typing into the terminal:
	```sh
	pip install -r requirements.txt
	```

4. Configure your account. Copy the `config.json.example` file to `config.json` then add your
   login details to the `accounts` section. If you are worried about getting banned from the
   temporary *teleportation*, you may want to find out your current location and change the config
   file accordingly. You can use either `latitude, longitude` format or just supply a name.

5. Use the tool! Type in the terminal: `python pogotools.py -h` for all the available options.

## Usage
Get a list of all your Pokemon sorted by their CP:
```sh
python pogotools.py -p
# or
python pogotools.py --get-pokemon
```

Get a list of all your Pokemon sorted by their real name or IV:
```sh
# For sort by real name:
python pogotools.py -p -s name
# For sort by IV:
python pogotools.py -p -s iv
```

Applying a filter to your list of Pokemon:
```sh
# Show only Pokemon below or equal to CP 1000
python pogotools.py -p --hide-cp-below 1000
# Show only Pokemon above or equal to CP 1000
python pogotools.py -p --hide-cp-below 1000
# Show only Pokemon below or equal to IV 70
python pogotools.py -p --show-iv-below 70
# Show only Pokemon above or equal to IV 70
python pogotools.py -p --hide-iv-below 70
```

These filters can be chained:
```sh
# Show only Pokemon above CP 1000 and above IV 70
python pogotools.py -p --hide-cp-below 1000 --hide-iv-below 70
```

Transfer Pokemon:
Make sure you have set the config file correctly for transfer to work.
This can be dangerous so make sure your criteria is actually what you want or your favourite Pikachu
may run away from you!
```sh
python pogotools.py --transfer
```

## Todo
- Evolve Pokemon
- Add tests
- Write proper documentation
- I have no idea what other tools I'm going to add yet but definitely more to come.

## Contributions
Feel free to add any extra tools to this! But please make sure it won't keep the user logged in
for a long time.

## Credits
- Many thanks to [tejado](https://github.com/tejado) for the API, this won't work without it.
