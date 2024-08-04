---
hide:
  - footer
---
# Daily

Used to fetch statistical data in daily chunks about market listings

`GET` > `/market/daily`

## Parameters
*♦ - required*

- ♦ `item` > `String` - Name of the item to get data of
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
    "absolute_average": 911.645,
    "absolute_max": 2999.0,
    "absolute_min": 700.0,
    "end": 1722200425,
    "iqr_average": 724.362,
    "iqr_max": 750.0,
    "iqr_min": 700.0,
    "listings": [
        {
            "created_at": 1722027123,
            "expired": true,
            "expires_at": 1722631923,
            "id": "ad273360-4ba1-11ef-8346-01005161a8df",
            "last_seen": 1722547393,
            "name": "Sticky Ichor",
            "price": 70000,
            "price_each": 700.0,
            "stack": 100,
            "type": "Crafting"
        },
        ...
    ],
    "start": 1722114463,
    "total_stack": 61737
}
```
Description: An array of objects per day tracked for the timedelta requested

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