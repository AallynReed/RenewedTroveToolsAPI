from beanie import Document, Indexed
from pydantic import BaseModel
from datetime import datetime


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
