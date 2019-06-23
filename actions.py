import utils
from utils import *


def act(player: NPC, universe, debug=0):  # NEURAL NET ARTIFICIAL BLOCKCHAIN FUCKING INTELLIGENCE
    if debug:
        print(f"NPC: {player.name} | Hunger: {player.hunger} | Thirst: {player.thirst} | Boredom: {player.boredom} | \
Arrows: {player.count_ammo('arrow')} | Bullets: {player.count_ammo('bullet')}")
        print(f"Usable weapons: {player.usable_weapons()}")
    options = get_options(player)

    # Weigh and score options // Int - ~[0-100]
    for i, option in enumerate(options):
        if option["action"] == "eat":
            options[i]["score"] = player.hunger
        elif option["action"] == "drink":
            options[i]["score"] = player.thirst
        elif option["action"] == "fill_drink":
            options[i]["score"] = player.thirst * 2 - player.drink_amount()
        elif option["action"] == "scavenge":
            # Sometimes the object has been scavenged first by someone else
            if option["object"] not in player.location.containers:
                del options[i]
                continue
            options[i]["score"] = 50 - ((player.hunger - player.food_amount()) * -0.1 +
                                        (player.thirst - player.drink_amount()) * -0.1 +
                                        len(player.inventory))
            # Choose reason for scavenging
            if player.hunger > 40 or player.thirst > 40:
                if player.hunger > player.thirst:
                    options[i]["reason"] = "food"
                else:
                    options[i]["reason"] = "drink"
            else:
                if len(player.inventory) < random.randrange(7):
                    options[i]["reason"] = "inventory"
        elif option["action"] == "socialize":
            relation = player.get_relation(option["object"])
            options[i]["score"] = player.loneliness // 2 + relation * (player.loneliness / 100)
        elif option["action"] == "attack":
            relation = player.get_relation(option["object"])
            options[i]["score"] = (100 - player.kindness) // 2 + relation * -2
            # options[i]["score"] = 200 # Debugging purposes. Rage mode.
        elif option["action"] == "travel":
            options[i]["score"] = 20 - (len(player.location.containers) * 5 +
                                        (len(player.location.players) - 1) * 10)
        elif option["action"] == "entertain":
            options[i]["score"] = player.boredom
        elif option["action"] == "scripted":
            options[i]["score"] = random.randrange(40) + player.boredom

    options = sorted(options, key=lambda k: k['score'], reverse=True)  # Sort options by score
    if debug == 2:
        for option in options:
            print(f"\t{color(str(option), Fore.LIGHTBLACK_EX)}")

    # Execute one of the most desired options
    action = options[min(max(random.randrange(-1, 2), 0), len(options) - 1)]
    if action["action"] == "eat":
        printd(
            f"NAME1 eats {color(player.eat(), Style.BRIGHT + Fore.CYAN)}.", [player])
    elif action["action"] == "drink":
        if action.get("object") is None:
            printd(rand_line("drink.desperation", [player]), [player])
            player.thirst = max(player.thirst - random.randrange(30, 70), 0)
        else:
            printd(rand_line("drink.consume", [player]), [player], water_amount=player.drink())
    elif action["action"] == "fill_drink":
        printd(rand_line("drink.refill", [player]), [player], item=action['object'].name)
        action["object"].water_oz = action["object"].effectiveness
    elif action["action"] == "scavenge":
        scavenge(player, action["object"], reason=action.get("reason"))
    elif action["action"] == "socialize":
        socialize(player, action["object"])
    elif action["action"] == "attack":
        attack(player, action["object"])
    elif action["action"] == "travel":
        explore(player, universe)
    elif action["action"] == "entertain":
        # TODO: Entertainment actions, the meat of the game
        printd("NAME1 acts like a big stupid clown.", [player])
        player.boredom = max(player.boredom - random.randrange(10, 30), 0)
    # Scripted actions
    elif action["action"] == "scripted":
        try:
            # If item has not been used
            if action["object"].script_object is None:
                # Instantiate script class
                action["object"].script_object = scripts[action["object"].id]()
            # Run script
            action["object"].script_object(player, universe, utils)
            # Remove from inventory if item is done existing
            if action["object"].script_object.done:
                player.inventory.remove(action["object"])
        except KeyError as e:
            raise Exception(f"Item '{e.args[0]}' contains incorrectly configured scripts.")


def get_options(player: NPC):
    options = []
    # See if eating/drinking are options
    for item in player.inventory:
        if item.type == "food":
            option = {"action": "eat"}
            if option not in options:
                options.append(option)
        elif item.type == "drink":
            if item.water_oz > 0:
                option = {"action": "drink"}
                if option not in options:
                    options.append(option)
            else:
                if player.location.biome.precipation > 30:
                    option = {"action": "fill_drink", "object": item}
                    if option not in options:
                        options.append(option)
        # Scripted items
        elif item.type == "scripted":
            options.append({"action": "scripted", "object": item})
    # If no drinks whatsoever
    if not any(option["action"] == "drink" for option in options):
        if player.location.biome.precipation > 30:
            options.append({"action": "drink"})

    # Look around the room for useful things
    for container in player.location.containers:
        option = {"action": "scavenge", "object": container}
        options.append(option)

    # Interact with other people
    for person in player.location.players:
        if person != player:
            options.append({"action": "socialize", "object": person})
            options.append({"action": "attack", "object": person})

    # Travel
    options.append({"action": "travel"})

    # Entertain
    # TODO: Add dynamic entertainment options based on items, people, and location
    options.append({"action": "entertain"})

    return options


def scavenge(player, con=None, reason=None):
    # State your objective
    if con is None:
        con = random.choice(player.location.containers)
    if reason is None:
        printd(rand_line("scavenge.general", [player]), [player], trailing=True, container=con.name)
    elif reason in ("food", "drink"):
        printd(rand_line("scavenge.food_or_drink", [player]), [player], reason=reason, trailing=True, container=con.name)
    elif reason == "inventory":
        printd(rand_line("scavenge.inventory", [player]), [player], trailing=True, container=con.name)
    # Pick up items
    if len(con.items) > 0:
        for con_item in con.items:
            printd(rand_line("scavenge.found", [player]), [player], leading=True, item=con_item.color_name)
            # If player can carry item
            if player.pickup(con_item):
                # Give starter ammo
                if con_item.is_weapon and con_item.requires_ammo:
                    free_ammo_amount = max(random.randrange(4) - 1, 0)
                    if free_ammo_amount > 0:
                        printd(rand_line("scavenge.found_amount", [player]), [player], leading=True,
                               item=Item(con_item.ammo_type).color_name, amount=free_ammo_amount)
                        for _ in range(free_ammo_amount):
                            player.pickup(Item(con_item.ammo_type))
                con.items.remove(con_item)
            else:
                printd(rand_line("scavenge.too_heavy", [player]), [player], leading=True)
            break # Only pick up one
    else:
        printd(rand_line("scavenge.empty"), [player], leading=True)
        player.location.containers.remove(con)
        return True


def explore(player, universe):
    choice = random.randrange(2)
    if choice == 0:
        location_choices = player.location.biome.locations.copy()
        location_choices.remove(player.location)
        player.move(random.choice(location_choices))
        printd(rand_line("explore.wander"), [player], location=player.location.color_name)
    elif choice == 1:
        new_coords = random.choice(walkable_coords(player, universe))
        location_choices = universe.biomes[new_coords[0]][new_coords[1]]
        # rand_line is called on a separate line from printd so that we can use the old location
        # for filtering before formatting the new one into the string and printing it. Genius.
        leaving_line = rand_line("explore.venture", [player])
        player.move(random.choice(location_choices.locations))
        printd(leaving_line, [player], location=player.location.color_name, biome=player.location.biome.color_name)


def attack(player, other_npc):
    # TODO: Check for weapon and ammo
    if len(player.usable_weapons()) > 0:  # If has weapon
        weapon = random.choice(player.usable_weapons())
        # Decide whether to scare or attack
        if random.choice([True, True, False, player.kindness < 50]):
            # Attack
            if weapon.requires_ammo:
                player.consume_ammo(weapon.ammo_type, amount=1)
            other_npc.damage(weapon.damage)
            printd(rand_line("attack.generic", [player, other_npc], item=weapon), [player, other_npc],
                   weapon=weapon.name)
            other_npc.interact(player, "friendly", -50)
            return True
        else:
            # Scare off
            choice = random.randrange(3)
            if choice == 0:
                # TODO: MAKE THIS ONLY WORK WITH GUNS
                printd("NAME1 fires a warning shot at NAME2.", [player, other_npc])
            elif choice == 1:
                printd("NAME1 screams and charges at NAME2 with HIS1 %s." % player.poll_inventory("tool")[0].name,
                       [player, other_npc])
            elif choice == 2:
                printd("NAME1 reveals HIS1 %s to NAME2 and requests HE2 leaves." % player.poll_inventory("tool")[
                    0].name, [player, other_npc])
            other_npc.interact(player, "friendly", -30)
            # TODO: Other responses for other_npc
            location_choices = other_npc.location.biome.locations.copy()
            location_choices.remove(other_npc.location)
            other_npc.move(random.choice(location_choices))
            printd(rand_line("explore.flee"), [other_npc], location=other_npc.location.color_name)
            return True
    else:  # If no weapon
        choice = random.randrange(2)
        if choice == 0:
            printd("NAME1 attacks NAME2 with HIS1 fists.", [player, other_npc])
            other_npc.damage(10)
            other_npc.interact(player, "friendly", -30)
            return True
        elif choice == 1:
            printd(rand_line("attack.insult", [player, other_npc]), [player, other_npc])
            other_npc.interact(player, "friendly", -10)
            return True
    # TODO: Other responses for other_npc


def socialize(player, other_npc):
    # If excess of resources
    if len(player.poll_inventory("food")) > 1 or len(player.poll_inventory("drink")) > 1:
        try:
            friends = player.relations[other_npc.name] > 20
        except KeyError:
            friends = False
        if friends or not player.does_evil():
            # Offer resource
            if len(player.poll_inventory("food")) > len(player.poll_inventory("drink")):
                printd("NAME1 offers some of HIS1 food to NAME2.", [player, other_npc])
                gift = player.poll_inventory("food")[0]
            else:
                printd("NAME1 offers some of HIS1 water to NAME2.", [player, other_npc])
                gift = player.poll_inventory("drink")[0]

            grateful = not other_npc.does_evil()  # Is the player grateful?

            # Other player "accepts"
            if random.choice([True, False]):
                # Evil opportunity
                if random.choice([True, False, other_npc.kindness < 50]):
                    printd("NAME2 accepts, and then %s." % (
                        "pours it on the ground" if gift.type == "drink" else "throws it away"), [player, other_npc])
                    player.interact(other_npc, "friendly", -20)
                    return True
                else:
                    if player.give(gift, other_npc):
                        printd("NAME2 accepts" + " and is greatful." if grateful else ".", [player, other_npc])
                        other_npc.interact(player, "friendly", 20 if grateful else 10)
                        player.interact(other_npc, "friendly", 10 if grateful else 5)
                        return True
                    else:
                        printd("NAME2 explains HE2 can't carry the gift" + " but appreciates the offer." if grateful
                               else ".", [player, other_npc])
                        other_npc.interact(player, "friendly", 20 if grateful else 5)
                        player.interact(other_npc, "friendly", 5)
                        return True
            else:
                printd("NAME2 declines" + " but expresses thanks." if grateful else ".", [player, other_npc])
                other_npc.interact(player, "friendly", 20 if grateful else 5)
                player.interact(other_npc, "friendly", 5)
                return True

    # Talk
    # TODO: Make this into a much bigger tree with variety in the conversation subjects
    printd("NAME1 talks to NAME2", [player, other_npc])
    other_npc.interact(player, "friendly", 5)
    player.interact(other_npc, "friendly", 5)
    return True
