from datetime import datetime, UTC, timedelta
import json


biome1 = [
    "Sundered Uplands",
    "Cerise Sandsea",
    "Deep Forest",
    "Alkali Flats",
    "Dead of Winter",
    "Sundered Uplands",
    "Firefly Party",
    "Desert of Secrets",
    "Weathered Wastelands",
    "Frozen Wastes",
    "Frigga's Fjord",
    "Abandoned Boneyard",
]
biome2 = [
    "Cursed Vale",
    "Hollow Dunes",
    "Bewitching Wood",
    "Primal Preserve",
    "Hollow Dunes",
    "Ancient Heights",
    "Viking Burial Grounds",
    "Spellbound Thicket",
    "Saurian Swamp",
    "Restless Range",
    "Uncanny Valley",
]
biome3 = [
    "Sugar Steppes",
    "Volcanic Fields",
    "The Lost Isles",
    "Luminopolis",
    "The Lost Isles",
    "Blazing Emberlands",
    "Cocoa Craters",
    "Data Spires",
    "The Lost Isles",
    "Cupcake Canyon",
    "Dragon's Teeth",
    "Luminopolis",
    "The Lost Isles",
    "Data Spires",
]

system_epoch = datetime.fromtimestamp(1718708400, UTC)
system_interval = 60 * 60 * 3


def get_rotation(now, consumed, elapsed, future=0):
    subbiomes = json.loads(open("versions/v1/data/biomes.json").read())
    start = now - timedelta(seconds=elapsed - (future * system_interval))
    end = start + timedelta(seconds=system_interval)
    _, biome1_index = divmod(consumed + future, len(biome1))
    _, biome2_index = divmod(consumed + future, len(biome2))
    _, biome3_index = divmod(consumed + future, len(biome3))
    first = biome1[biome1_index]
    second = biome2[biome2_index]
    third = biome3[biome3_index]
    return (
        int(start.timestamp()),
        int(end.timestamp()),
        subbiomes[first],
        subbiomes[second],
        subbiomes[third],
        future == 0,
    )
