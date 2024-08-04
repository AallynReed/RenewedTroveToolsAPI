---
hide:
  - footer
---
# Daily Graph

Used to fetch statistical data in daily chunks about market listings

`GET` > `/market/daily_graph`

## Parameters
*♦ - required*

- ♦ `item` > `String` - Name of the item to get data of
- `days` > `Integer` - Number of days to go back in history from **now**

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