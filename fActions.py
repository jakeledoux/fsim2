from fUtils import *


def act(player: NPC, debug=False):  # NEURAL NET ARTIFICIAL BLOCKCHAIN FUCKING INTELLIGENCE
    options = getOptions(player)

    # Weigh and score options // Int - ~[0-100]
    for i, option in enumerate(options):
        if option["action"] == "eat":
            options[i]["score"] = player.hunger
        elif option["action"] == "drink":
            options[i]["score"] = player.thirst
        elif option["action"] == "scavenge":
            options[i]["score"] = 100 - ((player.hunger - player.food_amount()) * -.05 +
                                         (player.thirst - player.drink_amount()) * -.05 +
                                         len(player.inventory) * 5)
        elif option["action"] == "socialize":
            try:
                relation = player.relations[option["object"].name].affinity
            except KeyError:
                relation = 0
            options[i]["score"] = player.loneliness // 2 + relation * (player.loneliness / 100)
        elif option["action"] == "attack":
            try:
                relation = player.relations[option["object"].name].affinity
            except KeyError:
                relation = 0
            options[i]["score"] = (100 - player.kindness) // 2 + relation * -0.5
        elif option["action"] == "travel":
            options[i]["score"] = 20 - (len(player.location.containers) * 5 +
                                        (len(player.location.players) - 1) * 10)

    options = sorted(options, key=lambda k: k['score'], reverse=True)  # Sort options by score

    # Execute one of the most desired options
    action = options[max(random.randrange(-1,2), 0)]
    if action["action"] == "eat":
        printd(
            f"NAME1 eats {color(player.eat(), Style.BRIGHT + Fore.MAGENTA)}.", [player])
    elif action["action"] == "drink":
        printd(f"NAME1 drinks {player.drink()} ounces of water.", [player])
    elif action["action"] == "scavenge":
        scavenge(player, action["object"])
    elif action["action"] == "socialize":
        printd("NAME1 talks to NAME2", [player, action["object"]])
        action["object"].interact(player, "friendly", 5)
    elif action["action"] == "attack":
        printd("NAME1 attacks NAME2", [player, action["object"]])
        action["object"].damage(10)
        action["object"].interact(player, "friendly", -30)
    elif action["action"] == "travel":
        player.move(action["object"])
        # BUG: IndexError: Cannot choose from an empty sequence
        printd(f"NAME1 wanders to {color(player.location.name, Style.BRIGHT + Fore.MAGENTA)}.", [player])
        player.hunger -= 10

    if debug:
        for option in options: print(option)


def getOptions(player: NPC):
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

    # Look around the room for useful things
    for container in player.location.containers:
        option = {"action": "scavenge", "object": container}
        options.append(option)

    # Interact with other people
    for person in player.location.players:
        if person != player:
            options.append({"action": "socialize", "object": person})
            options.append({"action": "attack", "object": person})

    # Possible travel destinations
    for location in player.location.biome.locations:
        if location == player.location:
            continue
        options.append({"action": "travel", "object": location})

    return options


def scavenge(player, con=None):
    if con == None:
        con = random.choice(player.location.containers)
    printd("NAME1 investigates a %s." % con.type, [player])
    for con_item in con.items:
        printd("HE1 found one %s!" % (Style.BRIGHT + Fore.CYAN + con_item.name + Style.RESET_ALL), [player])
        if not player.pickup(con_item):
            printd("But HE1 can't carry it.", [player])
        else:
            con.items.remove(con_item)
        break
    else:
        printd("There's nothing inside.")
        player.location.containers.remove(con)
        return True


def explore(player, universe):
    choice = random.randrange(3)
    if choice == 0:
        scavenge(player)
        player.hunger -= 5
    elif choice == 1:
        location_choices = player.location.biome.locations
        location_choices.remove(player.location)
        player.move(random.choice(location_choices))
        # BUG: IndexError: Cannot choose from an empty sequence
        printd("NAME1 wanders to %s." % (Style.BRIGHT + Fore.MAGENTA + player.location.name + Style.RESET_ALL),
               [player])
        player.hunger -= 10
    elif choice == 2:
        new_coords = random.choice(walkable_coords(player, universe))
        location_choices = universe.biomes[new_coords[0]][new_coords[1]]
        player.move(random.choice(location_choices.locations))
        printd(
            "NAME1 ventures out to " + Style.BRIGHT + Fore.MAGENTA + player.location.name + Style.RESET_ALL + ", in " + Style.BRIGHT + Fore.MAGENTA + location_choices.name + Style.RESET_ALL + ".",
            [player])
        player.hunger -= 30


def socialize(player, othernpc):
    if does_evil(player):  # Self-explanatory
        # TODO: Take friendship into account

        if len(player.poll_inventory("tool")) > 0:  # If has weapon
            if random.choice([True, False]):
                # Attack
                othernpc.damage(player.poll_inventory("tool")[0].effectiveness)
                printd("NAME1 attacks NAME2 with HIS1 %s." % player.poll_inventory("tool")[0].name, [player, othernpc])
                othernpc.interact(player, "friendly", -50)
                return True

            else:
                # Scare off
                choice = random.randrange(3)
                if choice == 0:
                    # TODO: MAKE THIS ONLY WORK WITH GUNS
                    printd("NAME1 fires a warning shot at NAME2.", [player, othernpc])
                elif choice == 1:
                    printd("NAME1 screams and charges at NAME2 with HIS1 %s." % player.poll_inventory("tool")[0].name,
                           [player, othernpc])
                elif choice == 2:
                    printd("NAME1 reveals HIS1 %s to NAME2 and requests HE2 leaves." % player.poll_inventory("tool")[
                        0].name, [player, othernpc])
                othernpc.interact(player, "friendly", -30)
                # TODO: Other responses for othernpc
                printd("NAME2 complies.", [player, othernpc])
                return True

        else:  # If no weapon
            pass
            choice = random.randrange(3)
            if choice == 0:
                printd("NAME1 attacks NAME2 with HIS1 fists.", [player, othernpc])
                othernpc.damage(10)
                othernpc.interact(player, "friendly", -30)
                return True
            elif choice == 1:
                printd("NAME1 attempts to intimidate NAME2 with HIS1 physical prowess.", [player, othernpc])
                othernpc.interact(player, "friendly", -10)
                return True
            elif choice == 2:
                printd("NAME1 insults NAME2.", [player, othernpc])
                othernpc.interact(player, "friendly", -10)
                return True
        # TODO: Other responses for othernpc

    else:

        # If excess of resources
        if len(player.poll_inventory("food")) > 1 or len(player.poll_inventory("drink")) > 1:
            try:
                friends = player.relations[othernpc.name] > 20
            except KeyError:
                friends = False
            if friends or not does_evil():

                # Offer resource
                if len(player.poll_inventory("food")) > len(player.poll_inventory("drink")):
                    printd("NAME1 offers some of HIS1 food to NAME2.", [player, othernpc])
                    gift = player.poll_inventory("food")[0]
                else:
                    printd("NAME1 offers some of HIS1 water to NAME2.", [player, othernpc])
                    gift = player.poll_inventory("drink")[0]

                grateful = does_evil(othernpc) == False  # Is the player grateful?

                # Other player "accepts"
                if random.choice([True, False]):
                    # Evil opportunity
                    if random.choice([True, False, othernpc.mean]):
                        printd("NAME2 accepts, and then %s." % (
                            "pours it on the ground" if gift.type == "drink" else "throws it away"), [player, othernpc])
                        player.interact(othernpc, "friendly", -20)
                        return True
                    else:
                        if player.give(gift, othernpc):
                            printd("NAME2 accepts" + " and is greatful." if grateful else ".", [player, othernpc])
                            othernpc.interact(player, "friendly", 20 if grateful else 10)
                            player.interact(othernpc, "friendly", 10 if grateful else 5)
                            return True
                        else:
                            printd(
                                "NAME2 explains HE2 can't carry the gift" + " but appreciates the offer." if grateful else ".",
                                [player, othernpc])
                            othernpc.interact(player, "friendly", 20 if grateful else 5)
                            player.interact(othernpc, "friendly", 5)
                            return True
                else:
                    printd("NAME2 declines" + " but expresses thanks." if grateful else ".", [player, othernpc])
                    othernpc.interact(player, "friendly", 20 if grateful else 5)
                    player.interact(othernpc, "friendly", 5)
                    return True

        # Talk
        # TODO: Make this into a much bigger tree with variety in the conversation subjects
        printd("NAME1 talks to NAME2", [player, othernpc])
        othernpc.interact(player, "friendly", 5)
        player.interact(othernpc, "friendly", 5)
        return True
    return False
