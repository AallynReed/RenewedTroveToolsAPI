---
hide:
  - footer
---
This object represents a leaderboard entry
#### **Structure**

- Fields
    - `uuid` >  `Integer` - In-game Integer ID of the leaderboard this entry is part of
    - `name_id` > `String` - In-game string ID of the leaderboard this entry is part of (In case name changes futurely)
    - `name` > `String` - Name of the leaderboard this entry is part of
    - `category_id` > `String` - In-game ID of the leaderboard category this entry is part of (In case name changes futurely)
    - `category` > `String` - Name of the leaderboard category this entry is part of
    - `player_name` > `String` - Name of the player
    - `rank` > `Integer` - Rank placement the player is in the leadeboard
    - `score` > `Float` - Score of the player for the leaderboard
    - `created_at` > `UTC Timestamp (seconds)` - When the entry was captured by bot

#### **Example**
```json
{
    "uuid": 1,
    "name_id": "Leaderboard_MetaExperience",
    "name": "TROVE MASTERY POINTS",
    "category_id": "Leaderboard_Category_Contests",
    "category": "TROVE MASTERY POINTS",
    "player_name": "karelm",
    "rank": 1,
    "score": 187060.0,
    "created_at": 1722682378,
}
```