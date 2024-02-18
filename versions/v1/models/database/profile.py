from beanie import Document, Indexed

from string import ascii_letters, digits
from random import choices

from datetime import datetime
from typing import Optional


def generate_id():
    return ''.join(choices(ascii_letters + digits, k=12))


class ModProfile(Document):
    profile_id: str = Indexed(str, unique=True, default_factory=generate_id)
    name: str
    description: str
    image_url: Optional[str] = None
    discord_id: int = Indexed(int)

    mod_hashes: list[str] = []

    shared: bool = False
    likes: list[int] = []
    deleted: bool = False
    clone_of: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @property
    def likes_count(self):
        return len(self.likes)