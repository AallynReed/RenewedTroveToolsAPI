---
hide:
  - footer
---
# Hourly Challenge History

Used to fetch the history of hourly challenges

`GET` > `/rotations/challenge/history`

## Success Response

**Code** : `200 OK`

#### **Content example**

Models: [`ChallengeEntry`](/models/rotations/ChallengeEntry) [`ChallengeType`](/models/rotations/ChallengeType)

- **Data**:
```json
[
    <ChallengeEntry>,
    ...
]
```
