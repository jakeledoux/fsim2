import utils
import actions

DEBUG_PRINTS = 0
DEBUG_SPEED = False

while True:
    universe = utils.World(1, 1)
    universe.players.append(utils.NPC('Jamie', 1))
    universe.players.append(utils.NPC('Barbara', 0))
    universe.players.append(utils.NPC('Steph', 0))

    for player in universe.players:  # Populate players
        player.random_location(universe)

    while True:
        # break # Remove if gameplay is desired.
        utils.clear()
        # MORNING
        if len(universe.players) == 0:
            print("Everyone has died. The end.")
            break
        else:
            for player in universe.players:  # Each player...
                # Remove dead player
                player.step()
                if player.dead:
                    universe.players.remove(player)
                    utils.printd(player.death_message, [player])
                    continue
                else:
                    actions.act(player, universe, debug=DEBUG_PRINTS)
                print()  # Creates newline, should be removed when GUI is worked on.
        if not DEBUG_SPEED:
            input("Press enter...")
    if not DEBUG_SPEED:
        break
