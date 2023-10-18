from beanie import Document
from pydantic import Field
from ...utils.functions import random_id


class StarBuild(Document):
    build: str = Field(default_factory=random_id)
    paths: list[str]
