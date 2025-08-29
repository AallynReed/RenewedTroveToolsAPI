from beanie import Document, Indexed, Link
from pydantic import BaseModel, computed_field, field_validator, Field
from typing import List
from enum import Enum


class LeaderboardType(Enum):
    DAILY = "Leaderboard_Category_Contests_Daily"
    WEEKLY = "Leaderboard_Category_Contests"
    DEFAULT = "DEFAULT"

    @classmethod
    def from_string(cls, name):
        for member in cls:
            if name == member.value:
                return member   
        return cls.DEFAULT


class ResetTime(Enum):
    DAILY = [
        # Leviathans
        32000
    ]
    WEEKLY = [
        # Delves
        2001, 2002, 2004, 2011, 2013, 2014, 2021, 2024,
        2300, 2301, 2302, 2303, 2304, 2305, 2306, 2307, 2308, 2309, 2310, 2311, 2312, 2313, 2314, 2315, 2316, 2317,
        2400, 2401, 2402, 2403, 2404, 2405, 2406, 2407, 2408, 2409, 2410, 2411, 2412, 2413, 2414, 2415, 2416, 2417,
        # Effort
        4000, 4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008, 4009, 4010, 4011, 4012, 4013, 4014, 4015, 4016, 4017,
        # Paragon
        5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010, 5011, 5012, 5013, 5014, 5015, 5016, 5017,
        # Stats
        10004, 10009, 10012, 10019, 21004, 21005, 21012, 30001, 30002, 30003, 30004, 30005, 33001, 33002, 50000
    ]
    DEFAULT = []

    @classmethod
    def match_value(cls, value):
        for group in cls:
            if value in group.value:
                return group
        return cls.DEFAULT


class Contest(BaseModel):
    time: int
    type: LeaderboardType

    @field_validator("type")
    def validate_type(cls, v):
        if not isinstance(v, LeaderboardType):
            return LeaderboardType.from_string(v)
        return v


class Leaderboard(Document):
    uuid: Indexed(int, unique=True)
    name_id: Indexed(str)
    name: str
    category_id: Indexed(str)
    category: str
    contests: List[Contest] = Field(default_factory=list, exclude=True)
    
    @computed_field
    @property
    def reset_time(self) -> str:
        return ResetTime.match_value(self.uuid).name
    
    @computed_field
    @property
    def player_leaderboard(self) -> bool:
        return not self.uuid in [1100, 21012]
        

class LeaderboardEntry(Document):
    player_name: str
    rank: Indexed(int)
    score: float
    leaderboard: Indexed(int)
    created_at: Indexed(int)


class LeaderboardEntryArchive(Document):
    player_name: str
    rank: Indexed(int)
    score: float
    leaderboard: Indexed(int)
    created_at: Indexed(int)
