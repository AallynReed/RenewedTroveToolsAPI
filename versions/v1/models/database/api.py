from beanie import Document, Indexed
from pydantic import BaseModel, Field
from datetime import datetime


class D15Biomes(BaseModel):
    current: list = Field(default_factory=list)
    previous: list = Field(default_factory=list)
    history: list = Field(default_factory=list)


class MasteryServer(BaseModel):
    live: int = 0
    pts: int = 0
    updated: datetime = 0


class Mastery(BaseModel):
    normal: MasteryServer
    geode: MasteryServer


class API(Document):
    id: str = Indexed(str, unique=True)
    mastery: Mastery
    downloads: int = 0
    biomes: D15Biomes
