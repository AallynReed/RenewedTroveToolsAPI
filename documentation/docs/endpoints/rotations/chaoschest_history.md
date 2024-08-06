---
hide:
  - footer
---
# Chaos Chest History

Used to fetch the history of chaos chests

`GET` > `/rotations/chaoschest/history`

## Success Response

**Code** : `200 OK`

#### **Content example**

Models: [`ChaosChestEntry`](/models/rotations/ChaosChestEntry)

- **Data**:
```json
[
    <ChaosChestEntry>,
    ...
]
```
