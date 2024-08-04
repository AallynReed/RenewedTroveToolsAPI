---
hide:
  - footer
---
# Listings

Used to fetch Trove's market listings

`GET` > `/market/listings`

## Parameters
*♦ - required*

- `item` > `String` - Name of the item to filter
- `limit` > `Integer` - Limit number of results (For paging/Lazy loading)
- `offset` > `Integer` - Skip number of results (For paging/Lazy loading)
- `price_min` > `Float` - Value for minimum price filter
- `price_max` > `Float` - Value for maximum price filter
- `created_after` > `UTC Timestamp [Seconds]` - When to start capturing based on creation date
- `created_before` > `UTC Timestamp [Seconds]` - When to stop capturing based on creation date
- `last_seen_before` > `UTC Timestamp [Seconds]` - When to start capturing based on last seen date
- `last_seen_after` > `UTC Timestamp [Seconds]` - When to stop capturing based on last seen date

## Success Response

**Code** : `200 OK`

#### **Content example**

Models: [`MarketListing`](/models/market/MarketListing)

- **Headers**:
```yaml
count: 0 # Amount of listings found in this request
```
- **Data**:
```json
[
    <MarketListing>,
    ...
]
```

Note: **May return empty array if misused**


## Error Response

**Condition** : If `price_min` greater than `price_max`

**Code** : `400 BAD REQUEST`

**Content** :

```json
{
  "message": "\"price_min\" can't be greater than \"price_max\"",
  "status_code": 400,
  "type": "error"
}
```

---

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

---

**Condition** : If `last_seen_before` less than `last_seen_after`

**Code** : `400 BAD REQUEST`

**Content** :

```json
{
  "message": "\"last_seen_before\" can't be greater than \"last_seen_after\"",
  "status_code": 400,
  "type": "error"
}
```