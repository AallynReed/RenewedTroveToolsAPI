---
hide:
  - footer
---
# Hourly Graph

Used to fetch statistical data in hourly chunks about market listings

`GET` > `/market/hourly_graph`

## Parameters
*♦ - required*

- ♦ `item` > `String` - Name of the item to get data of
- `hours` > `Integer` - Number of hours to go back in history from **now**

## Success Response

**Code** : `200 OK`

#### **Content example**

- **Returns**:
`Binary[Image] | PNG`

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