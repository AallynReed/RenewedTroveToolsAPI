---
hide:
  - footer
---
This object represents a set of (15) Long Shade biomes
#### **Structure**

- Fields `[Array]`
    - `start` > `UTC Timestamp (seconds)` - Time at which this rotation starts
    - `end` > `UTC Timestamp (seconds)` - Time at which this rotation ends
    - `first_biome` > [`D15Biome`](/models/misc/D15Biome) - First biome in the rotation
    - `second_biome` > [`D15Biome`](/models/misc/D15Biome) - Second biome in the rotation
    - `third_biome` > [`D15Biome`](/models/misc/D15Biome) - Third biome in the rotation
    - `is_current` > `Boolean` - Calculated price for each item based on `price` and `stack`

#### **Example**
```json
[
    1722704400,
    1722715200,
    {
        "biome": "Medieval Highlands",
        "caves": 0,
        "farm": 0,
        "final_name": "Medieval Highlands",
        "icon": "forest",
        "name": "Frigga's Fjord"
    },
    {
        "biome": "Fae Forest",
        "caves": 1,
        "farm": 1,
        "final_name": "Fae Forest",
        "icon": "fae",
        "name": "Spellbound Thicket"
    },
    {
        "biome": "Candoria",
        "caves": 0,
        "farm": 0,
        "final_name": "Candoria",
        "icon": "candy",
        "name": "Cocoa Craters"
    },
    true
]
```