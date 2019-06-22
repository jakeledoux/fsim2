from fUtils import *
from fActions import *

universe = world(1, 1)
universe.players.append(NPC('Jamie', 1))
universe.players.append(NPC('Barbara', 0))
universe.players.append(NPC('Steph', 0))

for player in universe.players:  # Populate players
    player.random_location(universe)

# print(universe.players[0].location.items)

while True:
    # break # Remove if gameplay is desired.
    clear()
    # MORNING
    for player in universe.players:  # Each player...
        # Remove dead player
        if player.dead:
            universe.players.remove(player)
            continue
        else:
            player.step()
        act(player, debug=True)
    input("Press enter...")
