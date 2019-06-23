import random


class DeathNote:
    def __init__(self):
        self.item_id = "death_note"
        self.target = None
        self.done = False

    def __call__(self, player, universe, utils):
        choice = random.randrange(5)
        # Death Note suicide
        if choice == 0:
            self.target = player
            utils.printd(utils.rand_line("mods.death_note.suicide"), [player])
        # Death Note homicide
        else:
            target_pool = [person for person in universe.players if person is not player]
            self.target = random.choice(target_pool)
            utils.printd(utils.rand_line("mods.death_note.general"), [player, self.target])
        # Kill target
        self.target.set_days_to_live(random.randrange(4) + 1, utils.rand_line("mods.death_note.death"))
        # Destroy book
        self.done = True


directory = [DeathNote]
