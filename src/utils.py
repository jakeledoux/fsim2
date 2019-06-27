import importlib
from typing import List, Dict, Tuple, Union
import colorama
import mimesis
import os
import random
import re
import sys
from colorama import Fore, Style

colorama.init(autoreset=True)

# RegEx Patterns
re_line_op = re.compile(r'<[^>]+>')
re_line_ext = re.compile(r'<([^>]+)>')
re_end_punct = re.compile(r'[.,!?;]$')
re_parens_int = re.compile(r'\((\d+)\)')
re_parens_str = re.compile(r'\((\D+)\)')
# Gets all parameters inside parenthesis
re_parens_params = re.compile(r'(?!.+\()([\w.]+)+(?:(?=.+\))|\))')

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
# Set path for external files if compiled with pyinstaller
CONFIG_PATH = os.path.dirname(sys.executable) if sys.executable.endswith("fsim2.exe") else BASE_PATH


# Exceptions
class StateMismatch(Exception):
    pass


class InventoryError(Exception):
    pass


class Line(object):
    """ Container object for Clem-formatted game text."""
    def __repr__(self):
        return f"<Line: {self.id}| Req: {self.requirements}| Act: {self.actions}| Ret: {self.returns}>"

    def __init__(self, line_id: str, line_text: str, line_requirements: List[str],
                 line_actions: List[str], line_returns: Dict[str, str]):
        """ Instantiates a line object. If you're using this, you're probably doing something wrong.
        This should only be used in :func:`utils.load_lines`.

        :param line_id: Text-ID for line. E.g. attack.generic or scavenge.too_heavy
        :param line_text: The body of the line. This is the text to be formatted and displayed.
        :param line_requirements: Clem format actions. E.g. biome:suburban or item:weapon:rifle
        :param line_actions: Clem format actions. E.g. do:consume:ammo(1) or do:pickup:axe
        :param line_returns: Clem format returns. E.g. return:limb:head
        """
        self.id = line_id
        self.text = line_text
        self.requirements = line_requirements
        self.actions = line_actions
        self.returns = line_returns
        # print(self)


def get_paren_int(intext: str) -> int:
    """ Extracts integers from parentheses. For use with Clem actions.

        :param intext: String to be checked. E.g. do:consume:ammo(1)
        :returns: Integer found inside parens.
    """
    return int(re_parens_int.search(intext).group(1))


def rand_line(*args, **kwargs) -> (str, Dict[str, str]):
    """
    Selects a relevant line and executes its actions
    More or less an alias for random.choice(get_lines()).text, see get_lines() documentation.

    :param args: Passes to get_lines()
    :param kwargs: Passes to get_lines()
    """
    line = random.choice(get_lines(*args, **kwargs))
    # Parse actions:
    try:
        player: NPC = args[1][0]
    except IndexError:
        player = None
    for action in line.actions:
        # Surface level actions
        if action.startswith("countdown"):
            # Modify existing countdown
            try:
                cd_selector, cd_action = action.split(":")
                [trait_name] = unpack_params(cd_selector)
                print("Selector, action:", cd_selector, cd_action)
                if cd_action.startswith("add"):
                    [amount] = unpack_params(cd_action)
                    player.get_traits(trait_name)[0].add(amount)
                elif cd_action.startswith("subtract"):
                    [amount] = unpack_params(cd_action)
                    player.get_traits(trait_name)[0].subtract(amount)
                elif cd_action.startswith("remove"):
                    player.traits.remove(player.get_traits(trait_name)[0])
            # Create new countdown
            except ValueError:
                name, action, days = unpack_params(action)
                player.traits.append(Trait(name, True, action, days))
        elif action.startswith("trait"):
            # Modify existing countdown
            try:
                cd_selector, cd_action = action.split(":")
                [trait_name] = unpack_params(cd_selector)
                if cd_action.startswith("remove"):
                    player.traits.remove(player.get_traits(trait_name)[0])
            # Create new countdown
            except ValueError:
                [name] = unpack_params(action)
                player.traits.append(Trait(name))
        # Categorical actions
        else:
            act_type, act_value = action.split(":")
            if act_type == "consume":
                if act_value.startswith("ammo"):
                    ammo_amount = get_paren_int(act_value)
                    if kwargs.get('item') is not None:
                        weapon = kwargs.get('item')
                    else:
                        weapon = player.get_weapon(['rifle', 'handgun', 'bow'])
                    player.consume_ammo(weapon.ammo_type, ammo_amount)
            elif act_type == "player":
                if act_value.startswith("die"):
                    player.die(announced=True)
    return line.text, line.returns


def unpack_params(intext: str) -> List[Union[str, int]]:
    """

    :param intext: String to extract from. E.g. countdown(poison, poison.die, 10)
    :return: List of parameters. E.g. ["poison", "poison.die", 10]
    """
    # TODO: Add bool and float support
    params = re_parens_params.findall(intext)
    params = [int(param) if param.isnumeric() else param for param in params]
    return params


def get_lines(line_id: str, players=None, item=None) -> List[Line]:
    """
    Filters game lines by line_id and requirements.

    :param line_id: The category of text to look for in the list.
    :param players: List of players relevant to this line. If omitted it will only return lines that don't have filters.
    :param item: For specific filters based on single objects selected by the game.
    :return: List of line objects meeting criteria.
    """
    # Most filtering will be based on subject player
    player: NPC = players[0] if players is not None else None
    out_lines = []
    # Iterate through all lines with same line_id (line_ids look like "drink.desperation")
    for line in lines[line_id]:
        req_results = []  # List with booleans, one for each requirement.
        if player is not None:
            for requirement in line.requirements:
                options = requirement.split("/")
                sub_results = []
                for option in options:
                    # Invert value if not: or !
                    if option.startswith("!") or option.startswith("not:"):
                        option = option.replace("!", "").replace("not:", "")
                        invert = True
                    else:
                        invert = False

                    # Store result before potentially inverting it later
                    sub_result = False

                    # Requirements are formatted as "type:value"
                    req_type, req_value = option.split(":", maxsplit=1)
                    if req_type == "biome":
                        sub_result = req_value == player.location.biome.type
                    elif req_type == "gender":
                        sub_result = req_value == ('female', 'male', 'other')[player.gender]
                    elif req_type == "weapon":
                        # Look through weapons in inventory and see if any match the specified type
                        if req_value.startswith("loaded"):
                            # Remove loaded keyword
                            req_value = req_value.split(":")[1]
                            # Get loaded weapons matching type
                            sub_result = len(player.usable_weapons([req_value])) > 0
                        else:
                            sub_result = any(inv_item.weapon_type == req_value for inv_item in player.inventory
                                             if inv_item.is_weapon)
                    elif req_type == "item":
                        req_type, req_value = req_value.split(":")
                        if req_type == "weapon":
                            sub_result = item.weapon_type == req_value
                    elif req_type == "player":
                        if req_value in ("arm", "arms", "leg", "legs", "head"):
                            # Limb checks
                            sub_result = player.poll_limbs()[req_value]
                        elif req_value == "limbless":
                            # Todo ignore head
                            sub_result = not all(player.poll_limbs())
                        elif req_value.startswith("trait") or req_value.startswith("countdown"):
                            [trait_name] = unpack_params(req_value)
                            sub_result = len(player.get_traits(trait_name)) > 0

                    # Append result
                    if invert:
                        sub_results.append(not sub_result)
                    else:
                        sub_results.append(sub_result)
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


def load_lines(*directory) -> Dict[str, List[Line]]:
    """ Parses Clem file into Line objects.

    :param directory: The directory to look in for 'lines.clem'.
    :return: Dictionary of lists of Line objects. The keys are derived from Line.id.
    """
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
                # Split by columns and strip whitespace
                line_data = [column.strip() for column in line.split("|")]
                # Get positional column data
                line_id, line_text, line_etc = line_data[0], line_data[1], line_data[2:]
                # Get all filter/requirement lines, i.e. not 'do:' or 'return:'
                line_requirements = [req for req in line_etc
                                     if not (req.startswith("do:") or req.startswith("return:"))]
                # Get all action lines, e.g. 'do:'
                line_actions = [act.strip("do:") for act in line_etc if act.startswith("do:")]
                # Get all return lines, e.g. 'return:' as dict of {category: value}
                line_returns = [ret.strip("return:") for ret in line_etc if ret.startswith("return:")]
                line_returns = {ret.split(":")[0].strip(): ret.split(":")[1].strip() for ret in line_returns}
                line_obj = Line(line_id, line_text, line_requirements, line_actions, line_returns)
                try:
                    output[line_data[0]].append(line_obj)
                except KeyError:
                    output[line_data[0]] = [line_obj]
        return output


def clear():
    """ Clears terminal."""
    os.system("cls" if os.name == "nt" else "clear")


def nest_split(intext, opening, closing, recursive=False):
    level = 0
    start_idx, end_idx = -1, -1
    for idx, char in enumerate(intext):
        if char == opening:
            if level == 0:
                start_idx = idx
            level += 1
        elif char == closing:
            level -= 1
            if level == 0:
                end_idx = idx
                break
    if start_idx == -1 or end_idx == -1:
        raise Exception("There are no complete opening/closing sets")
    else:
        output = intext.split(intext[start_idx:end_idx + 1])
        output.insert(0, intext[start_idx + 1:end_idx])
        if recursive and re_line_op.search(output[0]):
            output[0] = nest_split(output[0], opening, closing, True)
        return output


def shallow_split(intext: str, delimiter, opening, closing):
    level = 0
    for idx, char in enumerate(intext):
        if char == opening:
            level += 1
        elif char == closing:
            level -= 1
        elif char == delimiter and level == 0:
            return intext[:idx].strip(), intext[idx + 1:].strip()
    return [intext]


def printd(intext, players=(), trailing=False, leading=False, **kwargs):
    """ I still don't know why I originally called it printd instead of printf.
        The world may never know.
    """
    # Handle line returns
    if type(intext) is tuple:
        intext, line_returns = intext
    else:
        line_returns = None

    # Get both ends of string with pattern removed
    # While there are patterns in the text
    while re_line_op.search(intext):
        options, *sections = nest_split(intext, "<", ">")
        options = list(shallow_split(options, "/", "<", ">"))
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

    # Return line's return arguments
    return line_returns


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


class World:
    """ World object that the entire game exists within.
        Commonly referred to as "universe".
    """
    def __init__(self, size, biome_size):
        self.biomes: List[List[Biome]] = []
        self.players: List[NPC] = []
        self.size: Tuple[int, int] = size
        self.day: int = 0

        # Generate 2d array of biomes
        for x_coord in range(size):
            row = []
            for y_coord in range(size):
                row.append(Biome(biome_size, (x_coord, y_coord)))  # Generate Biome
            self.biomes.append(row)


class Biome:
    """ Biomes contain locations and subtly effect player actions."""
    def __repr__(self):
        return self.type + ":" + self.name

    def __init__(self, biome_size, world_coords: Tuple[int, int]):
        biome_types = ['urban', 'suburban', 'rural']
        self.type = random.choice(biome_types)
        self.name = Biome.gen_name(self.type)
        self.locations = []
        self.precipitation = (biome_types.index(self.type) + 1) * random.randrange(33)
        self.coords: Tuple[int, int] = world_coords
        # Generate locations in Biome
        for new_location in range(biome_size):
            self.locations.append(Location(self.type, self, street=True))
            self.locations.append(Location(self.type, self))

    @property
    def color_name(self):
        return Style.BRIGHT + Fore.MAGENTA + self.name + Style.RESET_ALL

    @staticmethod
    def gen_name(type_id: str) -> str:
        """ Generates name for biome.

        :param type_id: urban, suburban, or rural
        :return: Generated name
        """
        if type_id == "urban":
            return mimesis.Address().city()
        elif type_id == "suburban":
            return mimesis.Address().city() + " " + random.choice(['Estates', 'Town', 'Village', 'Suburbs', 'Hills'])
        elif type_id == "rural":
            return mimesis.Address().city() + " " + random.choice(
                ['Swamp', 'Mountain', 'Valley', 'Plains', 'Countryside'])


class Trait:
    def __repr__(self):
        if self.is_countdown:
            return f"<Countdown Trait: {self.id} | Days: {self.days_left}>"
        else:
            return f"<Trait: {self.id}>"

    def __init__(self, trait_id, is_countdown: bool = False, countdown_act: str = "", days: int = -1):
        """
        Traits allow meta attributes for characters without requiring physical items.

        :param trait_id: The name of the trait
        :param is_countdown: Whether the trait is a countdown or static
        :param countdown_act: What actions to execute once countdown finishes
        :param days: Days left on countdown
        """
        self.id = trait_id
        self.is_countdown = is_countdown
        self.countdown_act = countdown_act
        self.days_left = days

    def add(self, amount: int) -> None:
        """
        Extends countdown by a certain amount of days.

        :param amount: Days to extend by
        """
        if self.is_countdown:
            self.days_left += amount
        else:
            raise Exception("Cannot add days to non-countdown trait.")

    def subtract(self, amount: int) -> None:
        """
        Shortens countdown by a certain amount of days.

        :param amount: Days to extend by
        """
        if self.is_countdown:
            self.days_left -= amount
        else:
            raise Exception("Cannot subtract days from non-countdown trait.")


class Location:
    def __repr__(self):
        return self.type + ":" + self.name

    def __init__(self, type_id, parent_biome, street=False):

        self.players: List[NPC] = []
        self.containers = []
        self.biome: Biome = parent_biome

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


class Item:
    def __repr__(self):
        if self.type == "drink":
            return self.type + ":" + self.name + " (%s/%s) fl. oz" % (self.water_oz, self.effectiveness)
        else:
            return self.type + ":" + self.name

    def __init__(self, item_id, water_oz=None):
        """
        Item object. Stored within :class:`Container` or :class:`NPC` inventories.

        :param item_id: Type of item to be created. Defined in items.csv.
        :param water_oz: Amount of water contained if applicable. If not specified, a random amount will be chosen.
        """
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


class Container:
    def __init__(self, type_id: str, items: List[Item] = None, name: str = None, explicit: bool = False):
        """
        Container object

        :param type_id: Type of container (Unless corpse, will be overwritten if not explicit)
        :param items: Optional list of items to populate the container.
        :param name: Optional name of container
        :param explicit: Whether to use type_id
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


class Relation:
    def __repr__(self):
        return "Relationship" + str((self.type, self.affinity))

    def __init__(self, type_id, amount):
        self.type = type_id  # String - "friendly", "romantic"
        self.affinity = amount  # Int - [0-100]


class NPC:
    """ NPC object that exists in and manipulates the world.
        Commonly referred to as 'player'.
    """
    def __repr__(self):
        return 'NPC:' + self.name

    def __init__(self, name, gender, kindness=None, bicurious=None):
        """ Instantiates a player.

        :param name: Player's first name (properly capitalized)
        :param gender: 0 is female, 1 is male, 2 is other.
        :param kindness: Optional kindness level (0-100)
        :param bicurious: Optional bicurious flag. Essentially bisexuality.
        """

        # Identity
        self.name: str = name.strip()  # String
        self.gender: int = gender  # Int - 0:female, 1:male
        self.relations: Dict[str, Relation] = {}  # Dict - {"Other NPC's Name" : <Relation object>}
        # Example: {"Charlie":['friendly', 10], "Danny":['friendly', -50], "Susan":['romantic', 39]}
        self.kindness: int = kindness if kindness is not None else random.randint(0, 100)  # Int - [0-100]
        self.bicurious: bool = bicurious if bicurious is not None else (
                random.randrange(10) == 0)  # Bool (Defaults to 1 in 10 chance)
        self.extroversion: float = round(random.random(), 3)

        # Needs
        self.hunger: int = random.randrange(10)  # [0-100]
        self.thirst: int = random.randrange(10)  # [0-100]
        self.loneliness: int = random.randrange(10, 80) * self.extroversion  # [0-100]
        self.boredom: int = random.randrange(20, 40)  # [0-100]

        self.inventory: List[Item] = []
        self.traits: List[Trait] = []
        self.strength = 50 if self.gender == 1 else 40  # How much the NPC can carry without a Container
        self.location: Location = None  # Must be defined before game begins

        self.unconscious: bool = False
        self.dead: bool = False
        self.days_to_live: int = -1  # If positive it will count down until zero, and they will die.
        self.death_message: str = ""
        self.death_day: int = -1
        self.death_announced = False

        self.kills: int = 0

        # Dict - Int - >=10:nominal,0-10:broken,<=-1:dismembered
        # self.limbs = {'l_arm': 20, 'r_arm': 20, 'l_leg': 20, 'r_leg': 20, 'head': 20}
        # Actually maybe not that ^
        self.limbs = {'l_arm': 100, 'r_arm': 100, 'l_leg': 100, 'r_leg': 100, 'head': 100}

    def step(self):
        """ Iterate the player's needs (Should be called once per cycle/day)"""
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

        # Increment countdowns
        for trait in self.traits:
            if trait.is_countdown:
                trait.subtract(1)

        if self.hunger > 100:
            self.die("NAME1 died of hunger.")
        elif self.thirst > 100:
            self.die("NAME1 died of thirst.")

    def random_location(self, universe: World):
        """
        Moves the player to a random position in the universe.

        :param universe: Primary game world
        """
        self.move(random.choice(random.choice(random.choice(universe.biomes)).locations))

    def set_days_to_live(self, days: int, death_message: str) -> None:
        """
        Starts a death-countdown at the end of which the player will die.

        :param days: Number of days the player has to live
        :param death_message: Message to display upon death. Use :func:`utils.rand_line` instead of hard-coding this.
        """
        self.death_message = death_message
        self.days_to_live = days

    def die(self, death_message="", announced=False) -> None:
        """
        Cause player to die.

        :param death_message: Message to display upon death. Use :func:`utils.rand_line` instead of hard-coding this.
        :param announced: Whether it's already been said that the player died.
        """
        self.death_message = death_message
        self.death_announced = announced
        self.dead = True
        self.location.players.remove(self)
        self.location.containers.append(Container('corpse', self.inventory, f"{self.name}'s corpse"))

    def food_amount(self) -> int:
        """
        Polls total food in inventory.

        :return: Integer equal to the amount of food the player has.
        """
        amount = 0
        for thing in self.inventory:
            if thing.type == "food":
                amount += thing.effectiveness

        return amount

    def drink_amount(self) -> int:
        """
        Polls total drinkable fluids in inventory.

        :return: Integer equal to the amount of drinkable fluids the player has.
        """
        amount = 0
        for thing in self.inventory:
            if thing.type == "drink":
                amount += thing.water_oz

        return amount

    def damage(self, amount: int, limb: str = None):
        """
        Deal damage to NPC.

        :param amount: Amount of damage to inflict
        :param limb: Limb to damage - 'l_arm', 'r_arm', 'l_leg', 'r_leg', or 'head'
        :return: Nothing at the moment
        """
        if limb is None:
            limb = random.choice(['l_arm', 'r_arm', 'l_leg', 'r_leg', 'head'])
        self.limbs[limb] -= amount
        if self.limbs['head'] in range(1, 20):
            self.unconscious = True
            printd(rand_line("status.knockout", [self]), [self])
        elif self.limbs['head'] < 1:
            self.die("NAME1 dies from wounds to the head.")

        # Calculate strength loss if arms are damaged
        self.strength = 10 + (self.limbs['l_arm'] // 10) * 10 + (self.limbs['r_arm'] // 10) * 10

    def poll_limbs(self) -> Dict[str, bool]:
        """
        Identifies whether sections of the body work or not

        :return: Dictionary with "arm", "arms", "leg", "legs", "head" and their state as a bool.
        """
        limb_cond = {limb: limb_cond > 40 for limb, limb_cond in self.limbs.items()}
        conditions = {"arm": limb_cond['l_arm'] or limb_cond['r_arm'],
                      "arms": limb_cond['l_arm'] and limb_cond['r_arm'],
                      "leg": limb_cond['l_leg'] or limb_cond['r_leg'],
                      "legs": limb_cond['l_leg'] and limb_cond['r_leg'],
                      "head": limb_cond['head']}
        return conditions

    def wake_up(self) -> None:
        """ Cause player to wake up from being unconscious and set head health to 30."""
        if self.unconscious:
            self.unconscious = False
            self.limbs['head'] = 30
        else:
            raise StateMismatch("Player was not unconscious when told to wake up.")

    def move(self, new_location: Location) -> None:
        """
        Move player into location provided.

        :param new_location:
        """
        if self.location is not None:
            self.location.players.remove(self)
        self.location = new_location
        new_location.players.append(self)

    def interact(self, other_npc_name: str, relation_type: str, amount: int) -> None:
        """
        Modify relationship between player and other_npc.

        :param other_npc_name: Name of other NPC object.
        :param relation_type: Type of relationship.
        :param amount: Amount to add.
        """
        try:  # Try to add affinity
            self.relations[other_npc_name].affinity += amount
        except KeyError:  # If there's no relationship with that NPC, create one
            self.relations[other_npc_name] = Relation(relation_type, amount)
        self.loneliness = min(self.loneliness - 30, 0)

    def pickup(self, item: Union[Item, str]):
        """
        Add item to player's inventory

        :param item: Either existing item object or item ID to create an object with.
        """
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
        """ Consumes food from inventory."""
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
        """ Consumes drinkable fluid from inventory."""
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

    def give(self, thing: Item, other_npc: 'NPC'):
        """
        Give an item to another NPC.

        :param thing: Gift to give
        :param other_npc: Recipient of gift
        """
        if other_npc.pickup(thing):
            self.inventory.remove(thing)
            return True
        else:
            return False

    def poll_inventory(self, type_id) -> List[Item]:  # Return list of type of Item in inventory
        """
        Gets all items of type_id in inventory.

        :param type_id: Item ID to search for
        :return: List of items matched
        """
        output = []
        for thing in self.inventory:
            if thing.type == type_id:
                output.append(thing)
        return output

    def get_traits(self, trait_id=None) -> List[Trait]:  # Return list of type of Trait in inventory
        """
        Gets all traits of trait_id in inventory. Will return all traits if trait_id is ommitted.

        :param trait_id: Trait ID to search for.
        :return: List of traits matched
        """
        if trait_id is None:
            return self.traits.copy()
        else:
            output = []
            for trait in self.traits:
                if trait.id == trait_id:
                    output.append(trait)
            return output

    def does_evil(self, variability=75) -> bool:
        """
        Returns bool deciding whether or not to do an evil thing. Based on kindness formula.

        :param variability: Amount of randomness to introduce
        :return: Whether the evil act should be committed
        """
        v = variability
        k = self.kindness
        return ((random.random() * v - (v / 2)) + 25 + k / 2) < 50

    def get_relation(self, other_npc: 'NPC') -> int:
        """
        Return relation between self and another NPC

        :param other_npc: NPC to look up relationship for
        :return: Relationship level
        """
        try:
            return self.relations[other_npc.name].affinity
        except KeyError:
            return 0

    def count_ammo(self, ammo_type: str) -> int:
        """
        Polls inventory for ammo of specific type

        :param ammo_type: Type of ammo. Types are defined in weapons.csv and items.csv
        :return: Amount of matched ammo in inventory
        """
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

    def get_weapon(self, weapon_types=[]) -> Item:
        """
        Gets random weapon of specific type.

        :param weapon_types: List of desired weapon types.
        :return: Random matched weapon.
        """
        try:
            return random.choice(self.usable_weapons(weapon_types))
        except IndexError:
            raise InventoryError(f"Player has no weapon matching types {weapon_types}")

    def usable_weapons(self, weapon_types=[]) -> List[Item]:
        """
        Gets list of weapons of specific type.

        :param weapon_types: List of desired weapon types.
        :return: All matched weapons.
        """
        output = []
        for item in self.inventory:
            if item.is_weapon:
                # See if weapon matches filter
                if item.weapon_type in weapon_types or len(weapon_types) == 0:
                    if item.requires_ammo:
                        if self.count_ammo(item.ammo_type) >= 1:
                            output.append(item)
                    else:
                        output.append(item)
        return output

    def obituary(self) -> str:
        """ Generates obituary title for player. E.g. Chrundle the Great, Robert the Fearless."""
        # TODO: Add titles to player based on how they live
        return f"NAME1 the Great"


def walkable_coords(player: NPC, universe: World) -> List[Tuple[int, int]]:
    """ Returns adjacent biomes to player's location in Universe.

    :param player:
    :param universe: World that player exists in.
    :return: List of world coordinates that can be used to lookup biomes.
    """
    size = universe.size
    current_coords = list(player.location.biome.coords)
    output = list()
    output.append((max(size - 1, min(0, current_coords[0] - 1)), current_coords[1]))
    output.append((max(size - 1, min(0, current_coords[0] + 1)), current_coords[1]))
    output.append((current_coords[0], max(size - 1, min(0, current_coords[1] - 1))))
    output.append((current_coords[0], max(size - 1, min(0, current_coords[1] + 1))))

    return output


def color(intext: str, fore_color: int, bright: bool = False):
    """ Colors string

    :param intext: String to be colored
    :param fore_color: Colorama color to be used. E.g. Fore.BLACK
    :param bright:
    """
    return (Style.BRIGHT if bright else "") + fore_color + intext + Style.RESET_ALL


def load_data(*directory):
    """ Loads csv data files in directory.

    :param directory: String arguments that form a path
    """
    global item_data
    global weapon_data
    global location_types
    global container_types
    global pronoun_list
    global nouns
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


def load_settings(*directory) -> Dict[str, int]:
    """ Loads settings from directory.

    :param directory: String arguments that form a path
    """
    if len(directory) == 0:
        path = CONFIG_PATH
    else:
        path = os.path.join(*directory)
    params = {}
    if os.path.exists(os.path.join(path, "settings.ini")):
        with open(os.path.join(path, "settings.ini"), "r") as f:
            for line in f.read().splitlines():
                if line.strip().startswith("#") or line.strip() == "":
                    continue
                p_name, p_value = [p.strip() for p in line.split("=")]
                params[p_name] = int(p_value)
    else:
        raise Exception(f"settings.ini not found in {path}")
    return params


# Load mods
def load_mods():
    global scripts
    global lines
    mod_list = [mod.name for mod in os.scandir(os.path.join(CONFIG_PATH, "mods")) if os.path.isdir(mod)]
    for mod_name in mod_list:
        mod_dir = os.path.join(CONFIG_PATH, "mods", mod_name)
        # Get basic extensions
        load_data(mod_dir)
        lines.update(load_lines(mod_dir))
        # Get scripted actions
        sys.path.insert(0, mod_dir)
        try:
            importlib.reload(scripted_actions)
        except NameError:
            import scripted_actions
        for script in scripted_actions.directory:
            scripts[script().item_id] = script
        sys.path.pop(0)


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
