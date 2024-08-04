---
hide:
  - footer
---
This object represents a market listing
#### **Structure**

- Fields
    - `id` > `UUID v1` - ID of the listing in-game
    - `name` > `String` - Name of the item in the listing
    - `type` > `Optional[String]` - Type of item in the listing
    - `stack` > `Integer` - Amount of items being sold in the listing
    - `price` > `Integer` - Price of the listing
    - `price_each` > `Float` - Calculated price for each item based on `price` and `stack`
    - `created_at` > `UTC Timestamp (seconds)` - When the listing was created in-game
    - `last_seen` > `UTC Timestamp (seconds)` - When the item was last available in the market (Bot captured)
    - `expired` > `Boolean` - If a listing is expired either by game's limit or through last_seen inactive for 3 hours straight
    - `expires_at` > `UTC Timestamp (seconds)` - Calculated date of when a listing would expire based on when it was created

#### **Example**
```json
{
    "created_at": 1722334646,
    "expired": true,
    "expires_at": 1722939446,
    "id": "aec320c0-4e6d-11ef-8346-01005161a8df",
    "last_seen": 1722367868,
    "name": "Acrobat Bark",
    "price": 72000,
    "price_each": 1600.0,
    "stack": 45,
    "type": null
}
```