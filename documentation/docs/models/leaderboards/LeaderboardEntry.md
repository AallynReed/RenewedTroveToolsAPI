---
hide:
  - footer
---
This object represents a market listing
#### **Structure**

- Fields
    - `id` > `String` - Arbritary ID for the entry in my database
    - `leaderboard_id` > `String` - In-game ID of the leaderboard this entry is part of (In case name changes futurely)
    - `leaderboard_name` > `String` - Name of the leaderboard this entry is part of
    - `player_name` > `String` - Name of the player
    - `rank` > `Integer` - Rank placement the player is in the leadeboard
    - `score` > `Float` - Score of the player for the leaderboard
    - `created_at` > `UTC Timestamp (seconds)` - When the entry was captured by bot

#### **Example**
```json
{
    "created_at": 1722682378,
    "id": "66ae0c13f6e4b1c584e7d907",
    "leaderboard_id": "Leaderboard_MetaExperience",
    "leaderboard_name": "TROVE MASTERY POINTS",
    "player_name": "karelm",
    "rank": 1,
    "score": 187060.0
}
```