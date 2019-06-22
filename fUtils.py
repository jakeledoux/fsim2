import random, mimesis, colorama, os, sqlite3
from colorama import Fore, Style

colorama.init(autoreset=True)


def walkable_coords(player, universe):
    size = universe.size
    current_coords = list(player.location.biome.coords)
    output = []
    output.append([max(size - 1, min(0, current_coords[0] - 1)), current_coords[1]])
    output.append([max(size - 1, min(0, current_coords[0] + 1)), current_coords[1]])
    output.append([current_coords[0], max(size - 1, min(0, current_coords[1] - 1))])
    output.append([current_coords[0], max(size - 1, min(0, current_coords[1] + 1))])

    return output


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def does_evil(player):
    evil = random.choice([False, True])  # Roll for good or evil action
    if not evil and player.mean:  # Mean players get a second chance to be evil
        evil = random.choice([False, True])
    return evil


def printd(intext, players=[]):
    while "NAME" in intext:
        name_index = intext.index("NAME")
        intext = intext[:name_index] + Style.BRIGHT + Fore.YELLOW + players[
            int(intext[name_index + 4]) - 1].name + Style.RESET_ALL + intext[name_index + 5:]

    for PRONOUN in pronoun_list:
        while PRONOUN in intext:
            pronoun_index = intext.index(PRONOUN)
            if pronoun_index == 0:
                intext = intext[:pronoun_index] + pronoun_list[PRONOUN][
                    players[int(intext[pronoun_index + len(PRONOUN)]) - 1].gender].title() + intext[
                                                                                             pronoun_index + 1 + len(
                                                                                                 PRONOUN):]
            else:
                intext = intext[:pronoun_index] + pronoun_list[PRONOUN][
                    players[int(intext[pronoun_index + len(PRONOUN)]) - 1].gender] + intext[
                                                                                     pronoun_index + 1 + len(PRONOUN):]

    print(intext)
    return


def load_csv(filename):
    with open("data/" + filename + ".csv", "r") as f:
        filedata = f.read()
        filedata = filedata.split("\n")
        output = {}
        for line in filedata:
            if line != "":
                line_data = line.split(",")
                output[line_data[0]] = line_data[1:]
        return output


class gen:
    def location(type):
        if type == "grocery_store":
            return random.choice(nouns["grocery_store"])
        elif type == "gas_station":
            return random.choice(nouns["gas_station"])
        elif type == "farm":
            prefix = random.choice(nouns["farm_prefix"])
            name = mimesis.Person().last_name(gender="male")
            apostrophe = random.choice([True, False])
            name += "'s" if apostrophe else ""
            suffix = random.choice(nouns["farm_suffix"])
            suffix += "s" if suffix[-4:] == "Farm" and not apostrophe else ""
            return " ".join([prefix, name, suffix]).strip()
        elif type == "apartment_building":
            return mimesis.Address().street_name() + " " + random.choice(nouns["apartment_building"])
        elif type == "house":
            return mimesis.Person().last_name() + " Residence"
        elif type == "street":
            return mimesis.Address().street_name() + " " + random.choice(nouns["street"])

    def biome(type):
        if type == "urban":
            return mimesis.Address().city()
        elif type == "suburban":
            return mimesis.Address().city() + " " + random.choice(['Estates', 'Town', 'Village', 'Suburbs', 'Hills'])
        elif type == "rural":
            return mimesis.Address().city() + " " + random.choice(
                ['Swamp', 'Mountain', 'Valley', 'Plains', 'Countryside'])


class world:
    def __init__(self, size, biome_size):
        self.biomes = []
        self.players = []
        self.size = size

        # Generate 2d array of biomes
        for x_coord in range(size):
            row = []
            for y_coord in range(size):
                row.append(biome(biome_size, (x_coord, y_coord)))  # Generate biome
            self.biomes.append(row)


class biome:
    def __repr__(self):
        return self.type + ":" + self.name

    def __init__(self, biome_size, world_coords):
        biome_types = ['urban', 'suburban', 'rural']
        self.type = random.choice(biome_types)
        self.name = gen.biome(self.type)
        self.locations = []
        self.coords = world_coords
        # Generate locations in biome
        for new_location in range(biome_size):
            self.locations.append(location(self.type, self, street=True))
            self.locations.append(location(self.type, self))


class location:
    def __repr__(self):
        return self.type + ":" + self.name

    def __init__(self, type, parentbiome, street=False):

        self.players = []
        self.containers = []
        self.biome = parentbiome

        if street:
            self.type = "street"
        else:  # Get list of compatible locations
            compatible_locations = []
            for loc in location_types:
                if type in location_types[loc]:
                    compatible_locations.append(loc)
            self.type = random.choice(compatible_locations)  # Choose random compatible location
        self.name = gen.location(self.type)

        for con in range(random.randrange(2, 7)):  # Generate containers
            self.containers.append(container(self.type))


class container:
    def __repr__(self):
        return "Container"

    def __init__(self, type, items=None):
        self.items = [] if items == None else items

        if type != 'corpse':
            compatible_containers = []
            for con in container_types:
                if type in container_types[con]:
                    compatible_containers.append(con)
            self.type = random.choice(compatible_containers)  # Choose random compatible container

        if random.randrange(2) == 1:
            self.items.append(item(random.choice(list(itemdata))))


class item:
    def __repr__(self):
        if self.type == "drink":
            return self.type + ":" + self.name + " (%s/%s) fl. oz" % (self.water_oz, self.effectiveness)
        else:
            return self.type + ":" + self.name

    def __init__(self, id, water_oz=0):
        self.name = itemdata[id][0]  # String
        self.type = itemdata[id][1]  # String - "food","drink","tool","container"
        self.effectiveness = int(itemdata[id][2])  # Int
        self.weight = float(itemdata[id][3])  # Float - pounds
        self.poison = False  # ;)

        if self.type == "drink":
            self.drymass = self.weight
            self.water_oz = water_oz  # Int - fl. oz of water
            self.calc_weight()

    def calc_weight(self):  # Calculate weight of drink based on liquid inside
        self.weight = self.drymass + (self.water_oz / 16)


class relation:
    def __repr__(self):
        return "Relationship" + str((self.type, self.affinity))

    def __init__(self, type, amount):
        self.type = type  # String - "friendly", "romantic"
        self.affinity = amount  # Int - [0-100]


class NPC:
    def __repr__(self):
        return 'NPC:' + self.name

    def __init__(self, name, gender, kindness=None, bicurious=None):

        # Identity
        self.name = name  # String
        self.gender = gender  # Int - 0:female, 1:male
        self.relations = {}  # Dict - {"Other NPC's Name" : ['relationship type', int:strength]}
        # Example: {"Charlie":['friendly', 10], "Danny":['friendly', -50], "Susan":['romantic', 39]}
        self.kindness = kindness if kindness is not None else random.randint(0, 100)  # Int - [0-100]
        self.bicurious = bicurious if bicurious is not None else (
                    random.randrange(10) == 0)  # Bool (Defaults to 1 in 10 chance)
        self.extroversion = round(random.random(), 3)

        # Needs
        self.hunger = 0  # Int - [0-100]
        self.thirst = 0  # Int - [0-100]
        self.loneliness = random.randrange(10, 80) * self.extroversion  # Int - [0-100]

        self.inventory = []  # List - [item(),item(),item()]
        self.strength = 50 if self.gender == 1 else 40  # Int - How much the NPC can carry without a container
        self.location = None  # Location() - Must be defined before start of game

        self.unconscious = False
        self.dead = False

        # Dict - Int - >=10:nominal,0-10:broken,<=-1:dismembered
        self.limbs = {'l_arm': 20, 'r_arm': 20, 'l_leg': 20, 'r_leg': 20, 'head': 20}

    def step(self):  # Iterate the player's needs (Should be called once per cycle/day)
        self.hunger += 10
        self.thirst += 20
        if len(self.location.players) == 1:
            self.loneliness += 20 * self.extroversion
        else:
            self.loneliness += 5 * self.extroversion

    def random_location(self, universe):
        self.move(random.choice(random.choice(random.choice(universe.biomes)).locations))

    def die(self):
        self.dead = True
        self.location.players.remove(self)
        self.location.containers.append(container('corpse', self.inventory))

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
        if limb == None:
            limb = random.choice(['l_arm', 'r_arm', 'l_leg', 'r_leg', 'head'])
        self.limbs[limb] -= amount
        if self.limbs['head'] in range(1, 10):
            self.unconscious = True
        elif self.limbs['head'] < 1:
            self.die()

        # Calculate strength loss if arms are damaged
        self.strength = 10 + (self.limbs['l_arm'] // 10) * 10 + (self.limbs['r_arm'] // 10) * 10

    def move(self, new_location):
        if self.location != None:
            self.location.players.remove(self)
        self.location = new_location
        new_location.players.append(self)

    def interact(self, othernpc, relationtype, amount):  # Modify/create relationship
        try:  # Try to add affinity
            self.relations[othernpc].affinity += amount
        except KeyError:  # If there's no relationship with that NPC, create one
            self.relations[othernpc] = relation('friendly', amount)
        self.loneliness = min(self.loneliness - 30, 0)

    def pickup(self, item_id):
        try:
            item_id.upper()
            item_object = item(item_id)
        except:
            item_object = item_id
        # Calculate current weight of inventory
        inv_weight = 0
        if len(self.inventory) > 0:
            for thing in self.inventory:
                inv_weight += thing.weight
        # Check if player can hold new item
        if inv_weight + item_object.weight <= self.strength:
            self.inventory.append(item_object)
            return True
        else:
            return False

    def eat(self):
        food_item = None

        # Identify food item closest to hunger level
        for thing in self.inventory:
            if thing.type == "food":
                if food_item is None:
                    food_item = thing
                elif abs(thing.effectiveness - self.hunger) < abs(food_item.effectiveness - self.hunger):
                    food_item = thing

        if food_item is not None:  # If food item found
            self.hunger = max(self.hunger - food_item.effectiveness,
                              0)  # Replenish hunger, but don't let it become negative.
            self.inventory.remove(food_item)  # Remove consumed food item
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
        # Drink until no longer thirsty or run out of water, starting with container with fewest fl oz.
        for drink in water:
            if drink.water_oz >= self.thirst:  # If this current drink wil quench thirst
                oz_drank += self.thirst
                drink.water_oz -= self.thirst
                self.thirst = 0
                break  # Stop drinking
            else:  # If this current drink will not quench thirst
                oz_drank += drink.water_oz
                self.thirst -= drink.water_oz
                drink.water_oz = 0
        return oz_drank

    def give(self, thing, othernpc):
        if othernpc.inventory.pickup(thing):
            self.inventory.remove(thing)
            return True
        else:
            return False

    def poll_inventory(self, type):  # Return list of type of item in inventory
        output = []
        for thing in self.inventory:
            if thing.type == type:
                output.append(thing)
        return output


def color(intext, color):
    return color + intext + Style.RESET_ALL


# conn = sqlite3.connect('data.db')
itemdata = load_csv("items")
location_types = load_csv("locations")
container_types = load_csv("containers")
pronoun_list = load_csv("pronouns")
nouns = load_csv("nouns")
