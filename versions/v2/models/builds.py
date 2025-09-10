from pydantic import BaseModel
from .gems import (
    GemTier,
    GemType,
    GemElement,
    GemStatType,
    AugmentType,
    GemRestriction,
    GemAbility,
    GenerationType,
    Gem,
    ####
    GEM_STAT_RESTRICTIONS,
    GEM_TYPE_RESTRICTIONS,
    PHYSICAL_GEM_STAT_POOL,
    MAGIC_GEM_STAT_POOL,
    GEM_ABILITIES,
    LESSER_GENERATION_MODE,
    EMPOWERED_GENERATION_MODE,
    ####
    get_gem_max_level,
    get_increment_power_rank_lesser,
    get_increment_power_rank_empowered,
    get_stat_base_lesser,
    get_stat_base_empowered,
    get_stat_threshold_lesser,
    get_stat_threshold_empowered,
    get_lesser_gem_pr_threshold,
    get_empowered_gem_pr_threshold,
    get_augment_base
)
import itertools
from typing import Tuple, Iterable, Union
from random import choice, randint
import traceback


def _even_split(value: int, groups: int) -> Tuple[int, ...]:
    base, r = divmod(value, groups)
    return tuple([base + 1] * r + [base] * (groups - r))

def generate_combos():
    first_iter = ((i, 9 - i, 0) for i in range(10))
    second_iter = ((i, 18 - i, 0) for i in range(19))
    third_iter = ((0, 0, 3),)
    fourth_iter = ((0, 0, 6),)

    return itertools.product(first_iter, second_iter, third_iter, fourth_iter)

class GemBuild(BaseModel):
    combo: tuple

    @property
    def proc_distribution(self):
        final_distribution = []
        for combo in self.combo:
            total = sum(combo)
            num_stats = total // 3
            per_category = tuple(_even_split(v, num_stats) for v in combo)
            final_distribution.append(per_category)
        return tuple(final_distribution)

    def make_gem_set(self, restriction=None,generation_type=GenerationType.DAMAGE):
        if restriction is None:
            restriction = choice(list(GemRestriction))
        gem_set = []
        base_settings = {
            "tier": GemTier.MYSTIC,
            "restriction": restriction,
            "augmentation": 1,
            "level": 100
        }
        for i, combo in enumerate(self.combo):
            gem_count = sum(combo) // 3
            distributed = self.proc_distribution[i]
            dmg, crit, light = distributed
            if i in [0, 2]:
                base_settings["type"] = GemType.EMPOWERED
                generation_mode = EMPOWERED_GENERATION_MODE
            elif i in [1, 3]:
                base_settings["type"] = GemType.LESSER
                generation_mode = LESSER_GENERATION_MODE
            if i in [0, 1]:
                elements = [GemElement.FIRE, GemElement.WATER, GemElement.AIR]
            elif i in [2, 3]:
                elements = [GemElement.COSMIC]
            gems_per_element = gem_count // len(elements)
            x = 0
            for element in elements:
                for _ in range(gems_per_element):
                    procs = [dmg[x], crit[x], light[x]]
                    gem = Gem.create(element=element, generation=generation_mode[element][restriction][generation_type], procs=procs, **base_settings)
                    gem_set.append(gem)
        return gem_set
    
    def calculate_gem_stats(self):
        stats = {}
        for gem in self.make_gem_set():
            for stat in gem.stat_values:
                for k, v in stat.items():
                    if k not in stats:
                        stats[k] = 0
                    stats[k] += v
        for k, v in stats.items():
            stats[k] = v * 1.1
        return stats