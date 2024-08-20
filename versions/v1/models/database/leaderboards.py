from beanie import Document, Indexed


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
