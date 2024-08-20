---
hide:
  - footer
---
# List

Used to fetch Trove's leaderboard metadata

`GET` > `/leaderboards/list`

## Parameters
*♦ - required*

- `category_id` > `String` - ID of the leaderboard category to filter by
- `created_at` > `UTC Timestamp [Seconds]` - Day to extract leaderboard from. (Requires UTC or UTC+11 timestamp) which means it accepts 00:00 and 11:00 as valid entries.

## Success Response

**Code** : `200 OK`

#### **Content example**

Models: [`LeaderboardMetadata`](/models/leaderboards/LeaderboardMetadata)

- **Data**:
```json
[
    <LeaderboardItem>,
    ...
]
```