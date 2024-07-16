from pydantic import BaseModel
from enum import Enum
from typing import Optional
from itertools import product


class BuildType(Enum):
    light = "Light"
    farm = "Farming"
    tank = "Health"


class Class(Enum):
    bard = "Bard"
    boomeranger = "Boomeranger"
    candy_barbarian = "Candy Barbarian"
    chloromancer = "Chloromancer"
    dino_tamer = "Dino Tamer"
    dracolyte = "Dracolyte"
    fae_trickster = "Fae Trickster"
    gunslinger = "Gunslinger"
    ice_sage = "Ice Sage"
    knight = "Knight"
    lunar_lancer = "Lunar Lancer"
    neon_ninja = "Neon Ninja"
    pirate_captain = "Pirate Captain"
    revenant = "Revenant"
    shadow_hunter = "Shadow Hunter"
    solarion = "Solarion"
    tomb_raiser = "Tomb Raiser"
    vanguardian = "Vanguardian"


class GemBuildConfig(BaseModel):
    build_type: BuildType = BuildType.light
    character: Class = Class.bard
    subclass: Class = Class.boomeranger
    star_chart: Optional[str] = None
    food: str = "zephyr_rune"
    ally: str = "boot_clown"
    berserker_battler: bool = False
    critical_damage_count: int = 3
    no_face: bool = False
    light: int = 0
    subclass_active: bool = False
    litany: bool = False

    def __eq__(self, other):
        if not isinstance(other, GemBuildConfig):
            return False
        keys = self.__fields__.keys()
        for key in keys:
            if getattr(self, key) != getattr(other, key):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

def generate_combinations(farm=False):
    first_set = [[i, 9 - i] for i in range(10)]
    second_set = [[i, 18 - i] for i in range(19)]
    third_set = [
        [x, y, z]
        for x in range(4)
        for y in range(4)
        for z in range(4)
        if x + y + z == 3 and (z == 3 if not farm else True)
    ]
    fourth_set = [
        [x, y, z]
        for x in range(7)
        for y in range(7)
        for z in range(7)
        if x + y + z == 6 and (z == 6 if not farm else True)
    ]
    return product(first_set, second_set, third_set, fourth_set)