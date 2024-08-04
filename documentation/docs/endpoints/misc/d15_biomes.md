---
hide:
  - footer
---
# D15 Biomes

Used to fetch the long shade rotation

`GET` > `/misc/d15_biomes`

## Success Response

**Code** : `200 OK`

#### **Content example**

Models: [`D15BiomeSet`](/models/misc/D15BiomeSet)

- **Data**:
```json
{
    "current": <D15BiomeSet>,
    "next": <D15BiomeSet>,
    "history": [
        <D15BiomeSet>,
        ...
    ]

}
```

- **Example Return**

```json
{
  "current": [
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
  ],
  "history": [
    [
      1722650400,
      1722661200,
      {
        "biome": "Sundered Uplands",
        "caves": 0,
        "farm": 3,
        "final_name": "Sundered Uplands",
        "icon": "giantland",
        "name": "Sundered Uplands"
      },
      {
        "biome": "Fae Forest",
        "caves": 1,
        "farm": 0,
        "final_name": "Fae Forest",
        "icon": "fae",
        "name": "Bewitching Wood"
      },
      {
        "biome": "Dragonfire Peaks",
        "caves": 3,
        "farm": 2,
        "final_name": "Dragonfire Peaks",
        "icon": "dragon",
        "name": "Volcanic Fields"
      },
      false
    ],
    ...
  ],
  "next": [
    1722715200,
    1722726000,
    {
      "biome": "Desert Frontier",
      "caves": 1,
      "farm": 0,
      "final_name": "Desert Frontier",
      "icon": "frontier",
      "name": "Abandoned Boneyard"
    },
    {
      "biome": "Jurassic Jungle",
      "caves": 0,
      "farm": 0,
      "final_name": "Saurian Swamp",
      "icon": "dinosaur",
      "name": "Saurian Swamp"
    },
    {
      "biome": "Neon City",
      "caves": 0,
      "farm": 2,
      "final_name": "Neon City",
      "icon": "neon",
      "name": "Data Spires"
    },
    false
  ]
}
```