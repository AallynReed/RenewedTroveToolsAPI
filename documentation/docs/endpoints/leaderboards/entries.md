---
hide:
  - footer
---
# Entries

Used to fetch Trove's leaderboard entries

`GET` > `/leaderboards/entries`

## Parameters
*♦ - required*

- `name_id` > `String` - ID of the leaderboard to filter by
- `category_id` > `String` - ID of the leaderboard category to filter by
- `limit` > `Integer` - Limit number of results (For paging/Lazy loading)
- `offset` > `Integer` - Skip number of results (For paging/Lazy loading)
- `with_count` > `Int[0-1]` (Enabled by default) - Whether or not to return a header with amount of entries for the given query (Speeds up response time if disabled)
- `remove_fields` > `String` (Comma separated) - Comma Separated string of fields to exclude from the output object (Decreases response size and increases its speed)
- `created_at` > `UTC Timestamp [Seconds]` - Day to extract leaderboard from. (Requires UTC or UTC+11 timestamp) which means it accepts 00:00 and 11:00 as valid entries.

## Success Response

**Code** : `200 OK`

#### **Content example**

Models: [`LeaderboardEntry`](/models/leaderboards/LeaderboardEntry)

- **Headers**:
```yaml
count: 0 # Amount of entries found in this query regardless of limit
```
- **Data**:
```json
[
    <LeaderboardEntry>,
    ...
]
```

- Note:
    * **May return empty array if misused**
    * **Each entry will be stripped of a key in it's object model if that same value was used to query, in order to reduce payload**


## Error Response

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