from beanie import Document, Indexed
from pydantic import Field
from uuid import uuid4
from uuid import UUID
from typing import Union


class LeaderboardEntry(Document):
    uuid: Indexed(int)
    name_id: Indexed(str)
    name: str
    category_id: Indexed(str)
    category: str
    player_name: str
    rank: Indexed(int)
    score: float
    created_at: Indexed(int)
