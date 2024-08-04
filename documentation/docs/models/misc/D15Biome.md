---
hide:
  - footer
---
This object represents a (15) Long Shade biome
#### **Structure**

- Fields
    - `biome` > `String` - Name of general biome
    - `caves` > `Integer` - Rating of cave quality/quantity (more is better)
    - `farm` > `Integer` - Rating of how farmable the biome is (more is better)
    - `final_name` > `String` - Display name of biome
    - `icon` > `String` - Name of icon (used internally on my website)
    - `name` > `String` - Name of subbiome

#### **Example**
```json
{
    "biome": "Candoria",
    "caves": 0,
    "farm": 0,
    "final_name": "Candoria",
    "icon": "candy",
    "name": "Cocoa Craters"
}
```