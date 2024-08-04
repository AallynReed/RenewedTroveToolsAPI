from beanie import Document, Indexed
from pydantic import Field
from uuid import uuid4
from uuid import UUID


class LeaderboardEntry(Document):
    leaderboard_id: Indexed(str)
    leaderboard_name: str
    player_name: str
    rank: int
    score: float
    created_at: Indexed(int)
