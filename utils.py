from typing import List
import colorama
import mimesis
import os
import random
import re
import sys
from colorama import Fore, Style

colorama.init(autoreset=True)

# RegEx Patterns
re_line_op = re.compile("<[^>]+>")
re_line_ext = re.compile("<([^>]+)>")
re_end_punct = re.compile("[.,!?;]$")

BASE_PATH = os.path.dirname(os.path.realpath(__file__))


class Line(object):
    def __init__(self, line_id, line_text, line_requirements):
        self.id = line_id
        self.text = line_text
        self.requirements = line_requirements


def rand_line(*args, **kwargs):
    """ Alias for random.choice(get_lines()).text
    """
    return random.choice(get_lines(*args, **kwargs)).text


def get_lines(line_id: str, players=None, item=None) -> List[Line]:
    """
    :param line_id:
    The category of text to look for in the list.
    :param players:
    List of players relevant to this line. If omitted it will only return lines that don't have filters.
    :param item:
    For specific filters based on single objects selected by the game.
    :return:
    List of line objects meeting criteria.
    """
    # Most filtering will be based on subject player
    player = players[0] if players is not None else None
    out_lines = []
    # Iterate through all lines with same line_id (line_ids look like "drink.desperation")
    for line in lines[line_id]:
        req_results = []  # List with booleans, one for each requirement.
        if player is not None:
            for requirement in line.requirements:
                options = requirement.split("/")
                sub_results = []
                for option in options:
                    # Requirements are formatted as "type:value"
                    req_type, req_value = option.split(":", maxsplit=1)
                    if req_type == "biome":
                        sub_results.append(req_value == player.location.biome.type)
                    elif req_type == "gender":
                        sub_results.append(req_value == ('female', 'male', 'other')[player.gender])
                    elif req_type == "weapon":
                        # Look through weapons in inventory and see if any match the specified type
                        sub_results.append(any(inv_item.weapon_type == req_value for inv_item in player.inventory
                                               if inv_item.is_weapon))
                    elif req_type == "item":
                        req_type, req_value = req_value.split(":")
                        if req_type == "weapon":
                            sub_results.append(item.weapon_type == req_value)
                req_results.append(any(sub_results))

            # If all requirement booleans are true,
            # in other words, the test was passed.
            if all(req_results):
                out_lines.append(line)
        else:
            # No line requirements
            if len(line.requirements) == 0:
                out_lines.append(line)
    return out_lines


def load_lines(*directory):
    with open(os.path.join(*directory, f"lines.clem"), "r") as f:
        filedata = f.read()
        filedata = (line.strip() for line in filedata.splitlines())
        output = {}
        for line in filedata:
            # Line comments
            if line.startswith(("#", "(", ")", "[", "]")):
                continue
            # Has content
            elif line != "":
                line_data = [column.strip() for column in line.split("|")]
                line_obj = Line(line_data[0], line_data[1], line_data[2:])
                try:
                    output[line_data[0]].append(line_obj)
                except KeyError:
                    output[line_data[0]] = [line_obj]
        return output


def walkable_coords(player, universe):
    size = universe.size
    current_coords = list(player.location.biome.coords)
    output = list()
    output.append([max(size - 1, min(0, current_coords[0] - 1)), current_coords[1]])
    output.append([max(size - 1, min(0, current_coords[0] + 1)), current_coords[1]])
    output.append([current_coords[0], max(size - 1, min(0, current_coords[1] - 1))])
    output.append([current_coords[0], max(size - 1, min(0, current_coords[1] + 1))])

    return output


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def does_evil(player):
    # LEGACY DO NOT USE
    evil = random.choice([False, True])  # Roll for good or evil action
    if not evil and player.mean:  # Mean players get a second chance to be evil
        evil = random.choice([False, True])
    return evil


def printd(intext, players=(), trailing=False, leading=False, **kwargs):
    """ I still don't know why I originally called it printd instead of printf.
        The world may never know.
    """

    # Get both ends of string with pattern removed
    # While there are patterns in the text
    while re_line_op.search(intext):
        sections = re_line_op.split(intext, maxsplit=1)
        # Get pattern
        options = re_line_ext.search(intext).group(1)
        # Split into list of parts
        options = [option.strip() for option in options.split("/") if option.strip() != ""]
        if len(options) == 1:
            # If the pattern has no slashes it's optional, not a choice
            options.append("")
        # Take an option and reintegrate it
        sections.insert(1, random.choice(options))
        intext = "".join(sections).strip()
        # Remove double spaces
        intext = re.sub(' +', ' ', intext)
        # Remove spaces before punctuation
        intext = re.sub(' ([.,!?;])', r'\1', intext)

    # Substitute names
    try:
        while "NAME" in intext:
            name_index = intext.index("NAME")
            intext = intext[:name_index] + Style.BRIGHT + Fore.YELLOW + players[
                int(intext[name_index + 4]) - 1].name + Style.RESET_ALL + intext[name_index + 5:]
    except IndexError:
        raise ValueError("NPC object not provided to derive NAME from.")

    # Substitute pronouns
    try:
        for PRONOUN in pronoun_list:
            while PRONOUN in intext:
                pronoun_index = intext.index(PRONOUN)
                if pronoun_index == 0:
                    intext = intext[:pronoun_index] + pronoun_list[PRONOUN][
                        players[int(intext[pronoun_index + len(PRONOUN)]) - 1].gender].title() + \
                             intext[pronoun_index + 1 + len(PRONOUN):]
                else:
                    intext = intext[:pronoun_index] + pronoun_list[PRONOUN][
                        players[int(intext[pronoun_index + len(PRONOUN)]) - 1].gender] + \
                             intext[pronoun_index + 1 + len(PRONOUN):]
    except IndexError:
        raise ValueError("NPC object not provided to derive pronouns from.")

    # Format variables
    try:
        intext = intext.format(**kwargs)
    except KeyError as e:
        raise KeyError("Keyword argument '{e.args[0]}' was not provided for formatting.")

    # Trailing periods
    if trailing:
        intext = re_end_punct.sub(r"...", intext)
    # Leading periods
    if leading:
        intext = "    ..." + intext[0].lower() + intext[1:]

    # Output formatted string
    print(intext)


def load_csv(filename):
    with open(filename, "r") as f:
        filedata = f.read()
        filedata = (line.strip() for line in filedata.splitlines())
        output = {}
        for line in filedata:
            # Line comments
            if line.startswith("#"):
                continue
            # Has content
            elif line != "":
                line_data = [column.strip() for column in line.split(",")]
                output[line_data[0]] = line_data[1:]
        return output


def gen_location(type_id):
    if type_id == "grocery_store":
        return random.choice(nouns["grocery_store"])
    elif type_id == "gas_station":
        return random.choice(nouns["gas_station"])
    elif type_id == "farm":
        prefix = random.choice(nouns["farm_prefix"])
        name = mimesis.Person().last_name()
        apostrophe = random.choice([True, False])
        name += "'s" if apostrophe else ""
        suffix = random.choice(nouns["farm_suffix"])
        suffix += "s" if suffix[-4:] == "Farm" and not apostrophe else ""
        return " ".join([prefix, name, suffix]).strip()
    elif type_id == "apartment_building":
        return mimesis.Address().street_name() + " " + random.choice(nouns["apartment_building"])
    elif type_id == "house":
        return mimesis.Person().last_name() + " Residence"
    elif type_id == "street":
        return mimesis.Address().street_name() + " " + random.choice(nouns["street"])


def gen_biome(type_id):
    if type_id == "urban":
        return mimesis.Address().city()
    elif type_id == "suburban":
        return mimesis.Address().city() + " " + random.choice(['Estates', 'Town', 'Village', 'Suburbs', 'Hills'])
    elif type_id == "rural":
        return mimesis.Address().city() + " " + random.choice(
            ['Swamp', 'Mountain', 'Valley', 'Plains', 'Countryside'])


class World:
    def __init__(self, size, biome_size):
        self.biomes = []
        self.players = []
        self.size = size

        # Generate 2d array of biomes
        for x_coord in range(size):
            row = []
            for y_coord in range(size):
                row.append(Biome(biome_size, (x_coord, y_coord)))  # Generate Biome
            self.biomes.append(row)


class Biome:
    def __repr__(self):
        return self.type + ":" + self.name

    def __init__(self, biome_size, world_coords):
        biome_types = ['urban', 'suburban', 'rural']
        self.type = random.choice(biome_types)
        self.name = gen_biome(self.type)
        self.locations = []
        self.precipation = (biome_types.index(self.type) + 1) * random.randrange(33)
        self.coords = world_coords
        # Generate locations in Biome
        for new_location in range(biome_size):
            self.locations.append(Location(self.type, self, street=True))
            self.locations.append(Location(self.type, self))

    @property
    def color_name(self):
        return Style.BRIGHT + Fore.MAGENTA + self.name + Style.RESET_ALL


class Location:
    def __repr__(self):
        return self.type + ":" + self.name

    def __init__(self, type_id, parent_biome, street=False):

        self.players = []
        self.containers = []
        self.biome = parent_biome

        if street:
            self.type = "street"
        else:  # Get list of compatible locations
            compatible_locations = []
            for loc in location_types:
                if type_id in location_types[loc]:
                    compatible_locations.append(loc)
            self.type = random.choice(compatible_locations)  # Choose random compatible Location
        self.name = gen_location(self.type)

        for con in range(random.randrange(2, 7)):  # Generate containers
            self.containers.append(Container(self.type))

    @property
    def color_name(self):
        return Style.BRIGHT + Fore.MAGENTA + self.name + Style.RESET_ALL


class Container:
    def __init__(self, type_id, items=None, name=None, explicit=False):
        """ Explicit allows for directly annotating the container type
        """
        self.items = [] if items is None else items

        if type_id != 'corpse':
            if explicit:
                self.type = type_id
            else:
                compatible_containers = []
                for con in container_types:
                    if type_id in container_types[con]:
                        compatible_containers.append(con)
                self.type = random.choice(compatible_containers)  # Choose random compatible Container
        else:
            self.type = 'corpse'

        self.name = ""
        if name is not None:
            self.name = name
        else:
            if nouns.get(self.type) is not None:
                try:
                    self.name = random.choice(nouns.get(self.type))
                except IndexError:
                    print(f"{self.type} | {nouns.get(self.type)}")
            else:
                self.name = self.__repr__()

        if len(self.items) == 0:
            item_count = random.randrange(4)
            self.items += [Item(random.choice(list(item_data))) for _ in range(item_count)]

    def __repr__(self):
        return f"Container:{self.type}:{self.name}"


class Item:
    def __repr__(self):
        if self.type == "drink":
            return self.type + ":" + self.name + " (%s/%s) fl. oz" % (self.water_oz, self.effectiveness)
        else:
            return self.type + ":" + self.name

    def __init__(self, item_id, water_oz=None):
        self.id = item_id
        self.name = item_data[item_id][0]  # String
        self.type = item_data[item_id][1]  # String - "food","drink","tool","Container"
        self.effectiveness = int(item_data[item_id][2])  # Int
        self.weight = float(item_data[item_id][3])  # Float - pounds
        self.poison = False  # ;)
        self.is_weapon = False
        self.script_object = None

        if self.type == "drink":
            self.dry_mass = self.weight
            if water_oz is None:
                self.water_oz = random.randrange(self.effectiveness)  # Int - fl. oz of water
            else:
                self.water_oz = water_oz
            self.calc_weight()

        if self.id in weapon_data:
            self.is_weapon = True
            self.weapon_type = weapon_data[self.id][0]
            self.damage = int(weapon_data[self.id][1])
            self.ammo_type = weapon_data[self.id][2]
            self.requires_ammo = self.ammo_type != "none"

    @property
    def water_units(self):
        return self.water_oz * 5

    @property
    def color_name(self):
        return Style.BRIGHT + Fore.CYAN + self.name + Style.RESET_ALL

    def calc_weight(self):  # Calculate weight of drink based on liquid inside
        self.weight = self.dry_mass + (self.water_oz / 16)


class Relation:
    def __repr__(self):
        return "Relationship" + str((self.type, self.affinity))

    def __init__(self, type_id, amount):
        self.type = type_id  # String - "friendly", "romantic"
        self.affinity = amount  # Int - [0-100]


class NPC:
    def __repr__(self):
        return 'NPC:' + self.name

    def __init__(self, name, gender, kindness=None, bicurious=None):

        # Identity
        self.name = name  # String
        self.gender = gender  # Int - 0:female, 1:male
        self.relations = {}  # Dict - {"Other NPC's Name" : <Relation object>}
        # Example: {"Charlie":['friendly', 10], "Danny":['friendly', -50], "Susan":['romantic', 39]}
        self.kindness = kindness if kindness is not None else random.randint(0, 100)  # Int - [0-100]
        self.bicurious = bicurious if bicurious is not None else (
                random.randrange(10) == 0)  # Bool (Defaults to 1 in 10 chance)
        self.extroversion = round(random.random(), 3)

        # Needs
        self.hunger = random.randrange(10)  # Int - [0-100]
        self.thirst = random.randrange(10)  # Int - [0-100]
        self.loneliness = random.randrange(10, 80) * self.extroversion  # Int - [0-100]
        self.boredom = random.randrange(20, 40)

        self.inventory = []  # List - [Item(),Item(),Item()]
        self.strength = 50 if self.gender == 1 else 40  # Int - How much the NPC can carry without a Container
        self.location = None  # Location() - Must be defined before start of game

        self.unconscious = False
        self.dead = False
        self.days_to_live = -1  # If positive it will count down until zero, and they will die.
        self.death_message = ""

        # Dict - Int - >=10:nominal,0-10:broken,<=-1:dismembered
        self.limbs = {'l_arm': 20, 'r_arm': 20, 'l_leg': 20, 'r_leg': 20, 'head': 20}

    def step(self):  # Iterate the player's needs (Should be called once per cycle/day)
        if self.days_to_live > 0:
            self.days_to_live -= 1
        elif self.days_to_live == 0:
            self.die(self.death_message)

        self.hunger += random.randrange(3) + 3
        self.thirst += random.randrange(3) + 3
        # Boredom is capped so it doesn't interfere with the will to survive
        self.boredom = min(self.boredom + 10, 70)
        if len(self.location.players) == 1:
            self.loneliness += 20 * self.extroversion
        else:
            self.loneliness += 5 * self.extroversion

        if self.hunger > 100:
            self.die("NAME1 died of hunger.")
        elif self.thirst > 100:
            self.die("NAME1 died of thirst.")

    def random_location(self, universe):
        self.move(random.choice(random.choice(random.choice(universe.biomes)).locations))

    def set_days_to_live(self, days, death_message):
        self.death_message = death_message
        self.days_to_live = days

    def die(self, death_message):
        self.death_message = death_message
        self.dead = True
        self.location.players.remove(self)
        self.location.containers.append(Container('corpse', self.inventory, f"{self.name}'s corpse"))

    def food_amount(self):
        amount = 0
        for thing in self.inventory:
            if thing.type == "food":
                amount += thing.effectiveness

        return amount

    def drink_amount(self):
        amount = 0
        for thing in self.inventory:
            if thing.type == "drink":
                amount += thing.water_oz

        return amount

    def damage(self, amount, limb=None):
        if limb is None:
            limb = random.choice(['l_arm', 'r_arm', 'l_leg', 'r_leg', 'head'])
        self.limbs[limb] -= amount
        if self.limbs['head'] in range(1, 10):
            self.unconscious = True
        elif self.limbs['head'] < 1:
            self.die("NAME1 dies from wounds to the head.")

        # Calculate strength loss if arms are damaged
        self.strength = 10 + (self.limbs['l_arm'] // 10) * 10 + (self.limbs['r_arm'] // 10) * 10

    def move(self, new_location):
        if self.location is not None:
            self.location.players.remove(self)
        self.location = new_location
        new_location.players.append(self)

    def interact(self, other_npc, relation_type, amount):  # Modify/create relationship
        try:  # Try to add affinity
            self.relations[other_npc].affinity += amount
        except KeyError:  # If there's no relationship with that NPC, create one
            self.relations[other_npc] = Relation(relation_type, amount)
        self.loneliness = min(self.loneliness - 30, 0)

    def pickup(self, item):
        if type(item) == str:
            item_object = Item(item)
        else:
            item_object = item
        # Calculate current weight of inventory
        inv_weight = 0
        if len(self.inventory) > 0:
            for thing in self.inventory:
                inv_weight += thing.weight
        # Check if player can hold new Item
        if inv_weight + item_object.weight <= self.strength:
            self.inventory.append(item_object)
            return True
        else:
            return False

    def eat(self):
        food_item = None

        # Identify food Item closest to hunger level
        for thing in self.inventory:
            if thing.type == "food":
                if food_item is None:
                    food_item = thing
                elif abs(thing.effectiveness - self.hunger) < abs(food_item.effectiveness - self.hunger):
                    food_item = thing

        if food_item is not None:  # If food Item found
            self.hunger = max(self.hunger - food_item.effectiveness,
                              0)  # Replenish hunger, but don't let it become negative.
            self.inventory.remove(food_item)  # Remove consumed food Item
            return food_item.name
        else:  # No food in inventory
            return False

    def drink(self):
        water = []
        for thing in self.inventory:
            if thing.type == "drink":
                if thing.water_oz > 0:
                    water.append(thing)
        if len(water) == 0:  # If NPC has no water
            return 0
        water.sort(key=lambda x: x.water_oz)  # Sort water list by amount of water (ascending)

        oz_drank = 0
        # Drink until no longer thirsty or run out of water, starting with Container with fewest fl oz.
        for drink in water:
            if drink.water_units >= self.thirst:  # If this current drink wil quench thirst
                oz_drank += self.thirst
                drink.water_oz -= self.thirst / 2
                self.thirst = 0
                break  # Stop drinking
            else:  # If this current drink will not quench thirst
                oz_drank += drink.water_units
                self.thirst -= drink.water_units
                drink.water_oz = 0
        return oz_drank

    def give(self, thing, other_npc):
        if other_npc.inventory.pickup(thing):
            self.inventory.remove(thing)
            return True
        else:
            return False

    def poll_inventory(self, type_id):  # Return list of type of Item in inventory
        output = []
        for thing in self.inventory:
            if thing.type == type_id:
                output.append(thing)
        return output

    def does_evil(self, variability=75):
        v = variability
        k = self.kindness
        return ((random.random() * v - (v / 2)) + 25 + k / 2) < 50

    def get_relation(self, other_npc):
        try:
            return self.relations[other_npc.name].affinity
        except KeyError:
            return 0

    def count_ammo(self, ammo_type):
        return len([item for item in self.inventory if item.type == "ammo" and item.id == ammo_type])

    def consume_ammo(self, ammo_type, amount=1):
        if self.count_ammo(ammo_type) >= amount:
            for item in self.inventory:
                if item.type == "ammo":
                    if item.id == ammo_type:
                        self.inventory.remove(item)
                        amount -= 1
                        if amount == 0:
                            return True
        return False

    def usable_weapons(self):
        output = []
        for item in self.inventory:
            if item.is_weapon:
                if item.requires_ammo:
                    if self.count_ammo(item.ammo_type) >= 1:
                        output.append(item)
                else:
                    output.append(item)
        return output


def color(intext, fore_color, bright=False):
    return (Style.BRIGHT if bright else "") + fore_color + intext + Style.RESET_ALL


def load_data(*directory):
    global item_data
    global weapon_data
    global location_types
    global container_types
    global pronoun_list
    global nouns
    """
    :param directory:
    String arguments that form a path
    :return:
    """
    path = os.path.join(*directory)
    if os.path.exists(os.path.join(path, "items.csv")):
        item_data.update(load_csv(os.path.join(path, "items.csv")))
    if os.path.exists(os.path.join(path, "weapons.csv")):
        weapon_data.update(load_csv(os.path.join(path, "weapons.csv")))
    if os.path.exists(os.path.join(path, "locations.csv")):
        location_types.update(load_csv(os.path.join(path, "locations.csv")))
    if os.path.exists(os.path.join(path, "containers.csv")):
        container_types.update(load_csv(os.path.join(path, "containers.csv")))
    if os.path.exists(os.path.join(path, "pronouns.csv")):
        pronoun_list.update(load_csv(os.path.join(path, "pronouns.csv")))
    if os.path.exists(os.path.join(path, "nouns.csv")):
        nouns.update(load_csv(os.path.join(path, "nouns.csv")))


# Load main data
lines = load_lines(BASE_PATH, "data")
item_data = dict()
weapon_data = dict()
location_types = dict()
container_types = dict()
pronoun_list = dict()
nouns = dict()
scripts = dict()
load_data(BASE_PATH, "data")

# Load mods
mod_list = [mod.name for mod in os.scandir(os.path.join(BASE_PATH, "mods")) if os.path.isdir(mod)]
for mod_name in mod_list:
    mod_dir = os.path.join(BASE_PATH, "mods", mod_name)
    # Get basic extensions
    load_data(mod_dir)
    lines.update(load_lines(mod_dir))
    # Get scripted actions
    sys.path.insert(0, mod_dir)
    import scripted_actions
    for script in scripted_actions.directory:
        scripts[script().item_id] = script
    sys.path.pop(0)
