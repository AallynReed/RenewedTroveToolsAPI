from datetime import datetime, UTC, timedelta
import json


biomes = [
    "Desert Frontier",
    "The Lost Isles",
    "Geode Topside",
    "Neon City",
    "Dragonfire Peaks",
    "Permafrost",
    "Candoria",
    "Cursed Vale",
    "Forbidden Spires",
    "Fae Forest",
    "Medieval Highlands",
    "Jurassic Jungle",
    "Sundered Uplands"
]

STAMPY_MONDAY_EPOCH = datetime.fromtimestamp(1695639600, UTC)
STAMPY_SATURDAY_EPOCH = datetime.fromtimestamp(1696071600, UTC)
STAMPY_SUNDAY_EPOCH = datetime.fromtimestamp(1696158000, UTC)
STAMPY_MONDAY_INTERVAL = 14 * 24 * 60 * 60
STAMPY_SATURDAY_INTERVAL = 7 * 24 * 60 * 60
STAMPY_SUNDAY_INTERVAL = 7 * 24 * 60 * 60


def get_stampy_rotation(now, monday_consumed, monday_elapsed, saturday_consumed, saturday_elapsed, sunday_consumed, sunday_elapsed, future=0):
    subbiomes = json.loads(open("versions/v1/data/basic_biomes.json").read())
    monday_start = now - timedelta(seconds=monday_elapsed - (future * STAMPY_MONDAY_INTERVAL))
    monday_end = monday_start + timedelta(seconds=STAMPY_MONDAY_INTERVAL)
    saturday_start = now - timedelta(seconds=saturday_elapsed - (future * STAMPY_SATURDAY_INTERVAL))
    saturday_end = saturday_start + timedelta(seconds=STAMPY_SATURDAY_INTERVAL)
    sunday_start = now - timedelta(seconds=sunday_elapsed - (future * STAMPY_SUNDAY_INTERVAL))
    sunday_end = sunday_start + timedelta(seconds=STAMPY_SUNDAY_INTERVAL)
    _, monday_index = divmod(monday_consumed + future, len(biomes))
    _, saturday_index = divmod(saturday_consumed + future, len(biomes))
    _, sunday_index = divmod(sunday_consumed + future, len(biomes))
    monday = biomes[monday_index]
    saturday = biomes[saturday_index]
    sunday = biomes[sunday_index]
    return (
        int(monday_start.timestamp()),
        int(monday_end.timestamp()),
        subbiomes[monday],
        int(saturday_start.timestamp()),
        int(saturday_end.timestamp()),
        subbiomes[saturday],
        int(sunday_start.timestamp()),
        int(sunday_end.timestamp()),
        subbiomes[sunday],
        future == 0,
    )
