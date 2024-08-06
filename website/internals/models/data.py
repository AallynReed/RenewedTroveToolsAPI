from pydantic import BaseModel, Field
from typing import List, Optional


class Item(BaseModel):
    name: str
    tech_name: Optional[str] = None
    quantity_min: int
    quantity_max: int
    obtained: int
    hide: bool = False

    @property
    def average_quantity(self):
        if self.quantity_min == 0:
            return self.quantity_max
        return (self.quantity_min + self.quantity_max) / 2

    @property
    def technical_name(self):
        return self.tech_name if self.tech_name is not None else self.name


class Box(BaseModel):
    name: str
    opened: int
    loot_table: List[Item]

    @property
    def incorrect_data(self):
        i = 0
        for item in self.loot_table:
            i += item.obtained
        return not i == self.opened


class Drop(BaseModel):
    name: str
    opened: int
    loot_table: List[Item]

    @property
    def incorrect_data(self):
        return False


class Webpage(BaseModel):
    webpage: str
    name: str
    boxes: List[Box] = Field(default_factory=list)
    drops: List[Drop] = Field(default_factory=list)


class DataLoot(BaseModel):
    name: str
    tech_name: str
    total: int
    quantity_min: int
    quantity_max: int
    quantity: float
    obtained: int
    hide: bool

    @property
    def chance(self):
        return self.obtained / self.total

    @property
    def chance_str(self):
        return f"{round(self.chance * 100, 4)}%"

    @property
    def alt_chance(self):
        return self.total / self.obtained

    @property
    def alt_chance_str(self):
        return f"1 out of {round(self.alt_chance, 2):,}"

    @property
    def obtained_str(self):
        return f"{self.obtained:,}"


class DataTable(BaseModel):
    name: str = "Unknown Table"
    opened: int = 0
    loot: List[DataLoot] = Field(default_factory=list)

    @property
    def opened_str(self):
        return f"{self.opened:,}"

    @property
    def form_loot(self):
        form_loot_tech = []
        for loot in self.loot:
            if loot.hide:
                continue
            if loot.tech_name not in form_loot_tech:
                form_loot_tech.append([loot.tech_name, []])
            for loot_tech in form_loot_tech:
                if loot_tech[0] == loot.tech_name:
                    loot_tech[1].append([loot.chance, loot.quantity])
        for loot_tech in form_loot_tech:
            calculated_chance = 0
            for chance, quantity in loot_tech[1]:
                calculated_chance += quantity * chance
            loot_tech.append(round(calculated_chance, 5))
        form_loot_tech.sort()
        return form_loot_tech


class Table(BaseModel):
    data: Webpage
    table: List = Field(default_factory=list)

    @property
    def tables(self):
        tables = []
        for box in self.data.boxes:
            table = DataTable()
            table.name = box.name
            table.opened = box.opened
            for item in box.loot_table:
                loot = DataLoot(
                    name=item.name,
                    tech_name=item.technical_name,
                    total=box.opened,
                    quantity_min=item.quantity_min,
                    quantity_max=item.quantity_max,
                    quantity=item.average_quantity,
                    obtained=item.obtained,
                    hide=item.hide,
                )
                table.loot.append(loot)
            table.loot.sort(key=lambda x: x.chance)
            tables.append(table)
        for drop in self.data.drops:
            table = DataTable()
            table.name = drop.name
            table.opened = drop.opened
            for item in drop.loot_table:
                loot = DataLoot(
                    name=item.name,
                    tech_name=item.technical_name,
                    total=drop.opened,
                    quantity_min=item.quantity_min,
                    quantity_max=item.quantity_max,
                    quantity=item.average_quantity,
                    obtained=item.obtained,
                )
                table.loot.append(loot)
            table.loot.sort(key=lambda x: x.chance)
            tables.append(table)
        return tables

    @property
    def forms(self): ...
