---
hide:
  - footer
---
# Hourly

Used to fetch statistical data in hourly chunks about market listings

`GET` > `/market/hourly`

## Parameters
*♦ - required*

- ♦ `item` > `String` - Name of the item to get data of
- `hours` > `Integer` - Number of hours to go back in history from **now**
- `days` > `Integer` - Number of days to go back in history from **now**
- `no_listings` > `<No Value>` - If you want to reduce the payload and exclude array of listings

## Success Response

**Code** : `200 OK`

#### **Content example**

Models: [`MarketListing`](/models/market/MarketListing)

- **Data**:
```json
[
    {
        "absolute_average": <Float>,   # Average of price_each across all listings
        "absolute_max":     <Float>,   # Max price_each across all listings
        "absolute_min":     <Float>,   # Min price_each across all listings
        "end":              <Integer>, # End UTC timestamp of this block of listings
        "iqr_average":      <Float>,   # Average of price_each across all listings (Using IQR to remove outliers)
        "iqr_max":          <Float>,   # Max price_each across all listings (Using IQR to remove outliers)
        "iqr_min":          <Float>,   # Min price_each across all listings (Using IQR to remove outliers)
        "listings": [
            <MarketListing>,
            ...
        ],
        "start":            <Integer>, # Start UTC timestamp of this block of listings
        "total_stack":      <Integer>  # Total number of items across all listings
  }
]
```

- **Example**:
```json
{
    "absolute_average": 921.811,
    "absolute_max": 2999.0,
    "absolute_min": 650.0,
    "end": 1722713801,
    "iqr_average": 705.414,
    "iqr_max": 800.0,
    "iqr_min": 650.0,
    "listings": [
        {
            "created_at": 1722701901,
            "expired": false,
            "expires_at": 1723306701,
            "id": "c3f13720-51c4-11ef-ae1a-01005161a8df",
            "last_seen": 1722713253,
            "name": "Sticky Ichor",
            "price": 18850,
            "price_each": 650.0,
            "stack": 29,
            "type": "Crafting"
        },
        ...
    ],
    "start": 1722710202,
    "total_stack": 106324
}
```
Description: An array of objects per hour tracked for the timedelta requested

Note: **May return empty array if misused**


## Error Response

**Condition** : If `item` parameter was not defined

**Code** : `400 BAD REQUEST`

**Content** :

```json
{
  "message": "Missing Item",
  "status_code": 400,
  "type": "error"
}
``` 