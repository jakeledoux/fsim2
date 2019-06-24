from typing import List, Tuple

import utils
import actions

# CONFIGS ###################################################
# TODO: Move this to a config file
DEBUG_PRINTS = 0  # 0: Nothing, 1: Player states, 2: Decision scores
DEBUG_SPEED = 0  # 0: Normal gameplay, 1: Skip death-less recaps, 2: Skip recaps, 3: Wait for death, 4: Skip everything
MODS_ENABLED = False
RAGE_MODE = False
ONE_IN_THE_CHAMBER = False
WORLD_SIZE = 1
#############################################################

# LOAD GAME DATA ############################################
if MODS_ENABLED:
    utils.load_mods()
#############################################################

# INSTANTIATE GAME WORLD ####################################
while True:
    universe = utils.World(WORLD_SIZE, WORLD_SIZE)
    universe.players.append(utils.NPC('Jamie', 1))
    universe.players.append(utils.NPC('Barbara', 0))
    universe.players.append(utils.NPC('Steph', 0))

    for player in universe.players:  # Populate players
        player.random_location(universe)
        if ONE_IN_THE_CHAMBER:
            player.pickup(utils.Item("pistol"))
            player.pickup(utils.Item("bullet"))

    # GAME LOOP #################################################
    while True:
        utils.clear()
        universe.day += 1

        # MORNING
        if len(universe.players) == 0:
            print("Everyone has died. The end.")
            break
        else:
            utils.printd("Day {day}\n", day=universe.day)
            # Players to potentially skip
            skip_players: List[Tuple[str, utils.NPC]] = []
            # Stores players for their obituary
            funeral_parlor = []

            # Iterate through players in world
            # See https://github.com/jakeledoux/fsim2/issues/4 for explanation on why there's a .copy()
            for player in universe.players.copy():
                if player in skip_players:
                    continue

                # Remove dead player
                player.step()
                if player.dead:
                    universe.players.remove(player)
                    funeral_parlor.append(player)
                    player.death_day = universe.day
                    utils.printd(player.death_message, [player])
                    continue
                elif player.unconscious:
                    if utils.random.randrange(2):
                        utils.printd(utils.rand_line("status.wake_up", [player]), [player])
                        player.wake_up()
                    else:
                        utils.printd(utils.rand_line("status.unconscious", [player]), [player])
                else:
                    # Do turn
                    involved_players = actions.act(player, universe, debug=DEBUG_PRINTS, rage_mode=RAGE_MODE)

                    # Remove involved players from turn-pool
                    for inv_reason, inv_player in involved_players:
                        # Check if player has already been skipped
                        if inv_player not in skip_players:
                            # Skip if involved in social activity
                            if inv_reason == "socialize":
                                skip_players.append(inv_player)
                            # Skip if attacked only if unconscious
                            # See https://github.com/jakeledoux/fsim2/issues/8 for explanation
                            elif inv_reason == "attack":
                                if inv_player.unconscious:
                                    skip_players.append(inv_player)

                print()  # Creates newline, should be removed when GUI is worked on.
        if not DEBUG_SPEED >= 3:
            # This is where you'd put the call to flush text contents if working with a GUI.
            input("Press enter...")

        # Day recap ######################################################
        if len(universe.players) > 0:
            utils.clear()
            utils.printd(utils.rand_line("meta.day_end"), day=universe.day)
            if len(funeral_parlor) == 0:
                utils.printd(utils.rand_line("meta.everyone_survived"))
            else:
                utils.printd(utils.rand_line("meta.people_died"))
            for body in funeral_parlor:
                utils.printd(utils.obituary(body), [body])
            if DEBUG_SPEED == 0 or (DEBUG_SPEED in (1, 3) and len(funeral_parlor) > 0):
                input("Press enter...")
    # Play again?
    if DEBUG_SPEED < 4:
        break
#############################################################
