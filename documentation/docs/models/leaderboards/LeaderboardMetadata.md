---
hide:
  - footer
---
This object represents a leaderboard metadata entry
#### **Structure**

- Fields
    - `uuid` >  `Integer` - In-game Integer ID of the leaderboard this entry is part of
    - `name_id` > `String` - In-game string ID of the leaderboard this entry is part of (In case name changes futurely)
    - `category_id` > `String` - In-game ID of the leaderboard category this entry is part of (In case name changes futurely)
    - `count` > `UTC Timestamp (seconds)` - Amount of entries in the current query for this leaderboard

#### **Example**
```json
{
    "uuid": 1,
    "name_id": "Leaderboard_MetaExperience",
    "category_id": "Leaderboard_Category_Meta",
    "count": 5000
}
```