---
hide:
  - footer
---
# Entries

Used to fetch Trove's leaderboard entries

`GET` > `/leaderboards/entries`

## Parameters
*♦ - required*

- ♦ `uuid` > `Integer` - UUID of the leaderboard to fetch entries from.
- ♦ `created_at` > `UTC Timestamp [Seconds]` - Day to extract leaderboard from. (Requires UTC or UTC+11 timestamp) which means it accepts 00:00 and 11:00 as valid entries.
- `limit` > `Integer` - Limit number of results (For paging/Lazy loading)
- `offset` > `Integer` - Skip number of results (For paging/Lazy loading)

## Success Response

**Code** : `200 OK`

#### **Content example**

Models: [`LeaderboardEntry`](/models/leaderboards/LeaderboardEntry)

- **Data**:
```json
[
    <LeaderboardEntry>,
    ...
]
```

- Note:
    * **May return empty array if misused**


## Error Response

**Condition** : If `created_at` or `uuid` aren't defined

**Code** : `400 BAD REQUEST`

**Content** :

```json
{
  "message": "Missing uuid or created_at.",
  "status_code": 400,
  "type": "error"
}
```

---

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