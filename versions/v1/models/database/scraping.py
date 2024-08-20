from beanie import Document, Indexed
from pydantic import computed_field
from enum import Enum


class ChaosChestEntry(Document):
    item: str
    created_at: Indexed(int, unique=True)


class ChallengeType(Enum):
    COLLECTION = "Collection Challenge"
    RAMPAGE = "RAMPAGE ALERT!"
    RACING = "RACING"
    DUNGEON = "DUNGEON"

    @classmethod
    def from_string(cls, name):
        for member in cls:
            if name == member.value:
                return member
        return cls.DUNGEON


class ChallengeEntry(Document):
    name: str
    created_at: Indexed(int, unique=True)

    @computed_field
    @property
    def challenge_type(self) -> str:
        return ChallengeType.from_string(self.name).name
