---
hide:
  - footer
---
# List

Used to fetch Leaderboard fetch times, ordered by newest to oldest

`GET` > `/leaderboards/timestamps`

## Success Response

**Code** : `200 OK`

#### **Content example**

- **Data**:
```json
[
    <UTC Timestamp [TroveTime]>,
    <UTC Timestamp [TroveTime]>,
    ...
]
```