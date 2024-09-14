---
hide:
  - footer
---
This object represents a leaderboard's metadata
#### **Structure**

- Fields
    - `uuid` >  `Integer` - In-game Integer ID of the leaderboard this entry is part of
    - `name` > `String` - Name of the leaderboard this entry is part of
    - `name_id` > `String` - In-game string ID of the leaderboard this entry is part of (In case name changes futurely)
    - `category` > `String` - Name of the leaderboard category this entry is part of
    - `category_id` > `String` - In-game ID of the leaderboard category this entry is part of (In case name changes futurely)
    - `contest_type` > [`Optional[ContestType]`](/models/leaderboards/ContestType) - Type of contest if applicable for current timestamp, this may be null if it isn't a contest.
    - `player_leaderboard` > `Boolean` - Wether or not this leaderboard is a player leaderboard
    - `reset_time` > [`ResetTime`](/models/leaderboards/ResetTime) - Type of time reset this leaderboard has

#### **Example**
```json
{
    "uuid": 1,
    "category_id": "Leaderboard_Category_Meta",
    "category": "META",
    "name_id": "Leaderboard_MetaExperience",
    "name": "TROVE MASTERY POINTS",
    "contest_type": "WEEKLY",
    "player_leaderboard": false,
    "reset_time": "DEFAULT",
}
```