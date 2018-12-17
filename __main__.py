from fUtils import *
from fActions import *

universe = world(3,3)
universe.players.append(NPC('Jamie',1))
universe.players.append(NPC('Barbara',0))
universe.players.append(NPC('Steph',0))

for player in universe.players: # Populate players
	player.random_location(universe)

print(universe.biomes[0][0].locations)

while True:
	break # Remove if gameplay is desired.
	clear()
	# MORNING
	for player in universe.players: # Each player...

		# Remove dead player
		if player.dead:
			universe.players.remove(player)
			continue

		# If others are around
		if len(player.location.players) > 1:
			while True:
				othernpc = random.choice(player.location.players)
				if othernpc != player:
					break
			if socialize(player, othernpc):
				continue
			if player.hunger < 50:
				food_item = player.eat()
				if food_item != None:
					printd("NAME1 eats a %s." %(Style.BRIGHT+Fore.CYAN+food_item+Style.RESET_ALL),[player])
				else:
					printd("NAME1 is hungry.",[player])
			if player.thirst < 50:
				if player.drink():
					printd("NAME1 drinks some water.",[player])
				else:
					printd("NAME1 is thirsty.",[player])

		explore(player, universe)

	input("Press enter...")
