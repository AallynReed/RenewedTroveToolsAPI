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
- `created_after` > `UTC Timestamp [Seconds]` - When to start capturing based on creation date (Recommended start of UTC Day)
- `created_before` > `UTC Timestamp [Seconds]` - When to stop capturing based on creation date (Recommended end of UTC Day)

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