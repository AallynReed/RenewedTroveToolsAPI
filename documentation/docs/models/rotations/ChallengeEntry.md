---
hide:
  - footer
---
This object represents a hourly challenge entry
#### **Structure**

- Fields
    - `name` > `String` - Name of the hourly challenge
    - `challenge_type` > [`String[ChallengeType]`](/models/rotations/ChallengeType)
    - `created` > `UTC Timestamp (seconds)` - Hour at which this challenge showed up

#### **Example**
```json
{
    "name": "Collection Challenge",
    "challenge_type": "COLLECTION",
    "created_at": 1722945600
}
```