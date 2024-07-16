from beanie import Document
from pydantic import Field
from ...utils.functions import random_id
from pydantic import BaseModel


class Preset(BaseModel):
    toggle: bool = False
    name: str = "Starchart Build"
    order: int = 0


class StarBuild(Document):
    build: str = Field(default_factory=random_id)
    paths: list[str]
    preset: Preset = Field(default_factory=Preset)
