from enum import Enum


class StatID(Enum):
    maximum_health = 0
    physical_damage = 1
    magic_damage = 2
    critical_damage = 3
    critical_hit = 4
    attack_speed = 5
    movement_speed = 6
    light = 7
    # Coefficient is last stat in ID pool
    coefficient = 127


class StatName(Enum):
    maximum_health = "Maximum Health"
    physical_damage = "Physical Damage"
    magic_damage = "Magic Damage"
    critical_damage = "Critical Damage"
    critical_hit = "Critical Hit"
    attack_speed = "Attack Speed"
    movement_speed = "Movement Speed"
    light = "Light"
    # Coefficient is last stat in ID pool
    coefficient = "Coefficient"


class StatType(Enum):
    flat = 0
    bonus = 1
    class_bonus = 2
    post_bonus = 3


class Stat:
    def __init__(self, id: int, type: int, value: float = 0.0, raw_value: int = 0):
        self.id = id
        self.type = type
        self._value = raw_value or int(value * 1000)

    def __repr__(self):
        return f"<Stat id={self.name} type={self.type_name} value={self.value}>"

    @property
    def name(self):
        return StatName[StatID(self.id).name].value

    @property
    def type_name(self):
        return StatType(self.type).name

    @property
    def value(self):
        return round(self._value / 1000, 3)

    @value.setter
    def value(self, value: float):
        self._value = int(value * 1000)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=StatID[StatName(data["name"]).name].value,
            type=StatType[data["type"]].value,
            value=data["value"]
        )

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type_name,
            "value": self.value
        }

    @classmethod
    def decode(cls, encoded_value: int):
        stat_id = (encoded_value >> 57) & 0x7F
        stat_type = (encoded_value >> 54) & 0x07
        stat_value = encoded_value & ((1 << 51) - 1)
        if stat_value >= (1 << 50):
            stat_value -= (1 << 51)
        return cls(stat_id, stat_type, raw_value=stat_value)

    def encode(self):
        if not (0 <= self.id < 128):
            raise ValueError("stat id must be between 0 and 127")
        if not (0 <= self.type < 8):
            raise ValueError("stat type must be between 0 and 7")
        if not (-2 ** 50 <= self._value < 2 ** 50):
            raise ValueError("stat_value must fit in 51 bits as a signed integer")
        encoded_value = (self.id << 57) | (self.type << 54) | (self._value & ((1 << 51) - 1))
        return encoded_value


class Stats:
    def __init__(self, stats: list[Stat]=None):
        self.stats = stats or []

    def __repr__(self):
        return f"<Stats stats={self.stats}>"

    def calculate_stats(self):
        grouped_stats = {}
        for stat in self.stats:
            key = (stat.id, stat.type)
            grouped_stats[key] = grouped_stats.get(key, 0) + stat.value
        results = {}
        for stat_id in set(key[0] for key in grouped_stats.keys()):
            flat = grouped_stats.get((stat_id, StatType.flat.value), 0)
            bonus = grouped_stats.get((stat_id, StatType.bonus.value), 0)
            class_bonus = grouped_stats.get((stat_id, StatType.class_bonus.value), 0)
            post_bonus = grouped_stats.get((stat_id, StatType.post_bonus.value), 0)
            total = flat * (1 + bonus) * (1 + class_bonus) * (1 + post_bonus)
            results[stat_id] = total
        return [Stat(id=stat_id, type=StatType.flat.value, value=total) for stat_id, total in results.items()]
    
    def add_stat(self, stat: Stat):
        self.stats.append(stat)

