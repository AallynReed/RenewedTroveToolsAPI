---
hide:
  - footer
---
# Entries

Used to fetch Trove's leaderboard entries

`GET` > `/leaderboards/entries`

## Parameters
*♦ - required*

- `leaderboard_id` > `String` - ID of the leaderboard to filter
- `limit` > `Integer` - Limit number of results (For paging/Lazy loading)
- `offset` > `Integer` - Skip number of results (For paging/Lazy loading)
- `created_at` > `UTC Timestamp [Seconds]` - Day to extract leaderboard from. (Requires UTC or UTC+11 timestamp) which means it accepts 00:00 and 11:00 as valid entries.

## Success Response

**Code** : `200 OK`

#### **Content example**

Models: [`LeaderboardEntry`](/models/leaderboards/LeaderboardEntry)

- **Headers**:
```yaml
count: 0 # Amount of entries found in this request
```
- **Data**:
```json
[
    <LeaderboardEntry>,
    ...
]
```

Note: **May return empty array if misused**


## Error Response

**Condition** : If `created_before` less than `created_after`

**Code** : `400 BAD REQUEST`

**Content** :

```json
{
  "message": "\"created_before\" can't be greater than \"created_after\"",
  "status_code": 400,
  "type": "error"
}
```

**Condition** : If `created_at` is timestamp of any hour that's not 00:00 AM or 11:00 AM

**Code** : `400 BAD REQUEST`

**Content** :

```json
{
  "message": "Invalid timestamp, please give either UTC midnight or 11am (Trove time).",
  "status_code": 400,
  "type": "error"
}
```