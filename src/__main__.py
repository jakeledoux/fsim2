from typing import List, Tuple
from colorama import Fore, Back, Style
import actions
import utils
import robco

# CONFIGS ###################################################
settings = utils.load_settings()
#############################################################

# LOAD GAME DATA ############################################
if settings["MODS_ENABLED"]:
    utils.load_mods()
#############################################################

# INSTANTIATE GAME WORLD ####################################
while True:
    universe = utils.World(settings["WORLD_SIZE"], settings["WORLD_SIZE"])
    universe.players.append(utils.NPC('Jamie', 1))
    universe.players.append(utils.NPC('Barbara', 0))
    universe.players.append(utils.NPC('Steph', 0))

    for player in universe.players:  # Populate players
        player.random_location(universe)
        if settings["ONE_IN_THE_CHAMBER"]:
            player.pickup(utils.Item("pistol"))
            player.pickup(utils.Item("bullet"))

    # INSTANTIATE TERMINAL #####################################
    try:
        terminal = robco.Terminal("Fallout Simulator 2", font=utils.os.path.join(utils.BASE_PATH, "scp-sb.ttf"),
                                  fps=60, blocking=True, slow=True, chars_per_frame=3, post_processing=False)
        utils.terminal = terminal
        terminal.fix_height_char()
        terminal.println(f"Welcome to {Fore.GREEN + Style.BRIGHT}Fallout Simulator 2!")
        terminal.wait_for_enter()

        # GAME LOOP #################################################
        while True:
            utils.clear()
            universe.day += 1

            # MORNING
            if len(universe.players) == 0:
                print("Everyone has died. The end.")
                break
            else:
                # DAWN
                utils.printd(utils.rand_line("meta.day_start"), day=universe.day)
                utils.printd("Remaining contestants:")
                for player in universe.players:
                    if not player.dead:
                        utils.printd(f"    NAME1", [player])
                terminal.wait_for_enter()
                utils.clear()

                # DAYBREAK

                # Players to potentially skip
                skip_players: List[Tuple[str, utils.NPC]] = []
                # Stores players for their obituary
                funeral_parlor = []

                # Iterate through players in world
                # See https://github.com/jakeledoux/fsim2/issues/4 for explanation on why there's a .copy()
                for player in universe.players.copy():
                    if player in skip_players:
                        continue

                    # Remove dead player pre-turn
                    player.step()
                    if player.dead:
                        universe.players.remove(player)
                        funeral_parlor.append(player)
                        player.death_day = universe.day
                        if not player.death_announced:
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
                        involved_players = actions.act(player, universe, debug=settings["DEBUG_PRINTS"],
                                                       rage_mode=settings["RAGE_MODE"])

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

                    # Post turn
                    if player.dead and player.death_announced:
                        universe.players.remove(player)
                        funeral_parlor.append(player)
                        player.death_day = universe.day
                        if not player.death_announced:
                            utils.printd(player.death_message, [player])

                    print()  # Creates newline, should be removed when GUI is worked on.
            if not settings["DEBUG_SPEED"] >= 3:
                # This is where you'd put the call to flush text contents if working with a GUI.
                # input("Press enter...")
                terminal.wait_for_enter()
            # Day recap ######################################################
            if len(universe.players) > 0:
                utils.clear()
                utils.printd(utils.rand_line("meta.day_end"), day=universe.day)
                if len(funeral_parlor) == 0:
                    utils.printd(utils.rand_line("meta.everyone_survived"))
                else:
                    utils.printd(utils.rand_line("meta.people_died"))
                for body in funeral_parlor:
                    utils.printd(body.obituary(), [body])
                if settings["DEBUG_SPEED"] == 0 or (settings["DEBUG_SPEED"]in (1, 3) and len(funeral_parlor) > 0):
                    terminal.wait_for_enter()
        # Play again?
        if settings["DEBUG_SPEED"]< 4:
            break

    except robco.TerminalClose:
        print("Goodbye.")
    terminal.close()
    break
#############################################################
