from __future__ import annotations

from beanie import Document, Indexed, Link, Insert, Update, Replace, before_event
from pydantic import Field
from .mod import ModEntry

from string import ascii_letters, digits
from random import choices

from datetime import datetime, UTC
from typing import Optional, Annotated


def generate_id():
    return "".join(choices(ascii_letters + digits, k=12))


class ModProfile(Document):
    profile_id: Annotated[str, Indexed()] = Field(default_factory=generate_id)
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    owner_id: Annotated[int, Indexed()]

    mods: Annotated[list[Link[ModEntry]], Field(default_factory=list)]
    private_mods: Annotated[list[Link[ModEntry]], Field(default_factory=list)]
    sync_profile: bool = False

    shared: bool = False
    likes: Annotated[list[int], Field(default_factory=list)]
    deleted: bool = False
    clone_of: Optional[Link[ModProfile]] = None
    created: int = 0
    updated: int = 0

    @property
    def likes_count(self):
        return len(self.likes)

    @property
    def created_at(self):
        return datetime.fromtimestamp(self.created, UTC)

    @property
    def updated_at(self):
        return datetime.fromtimestamp(self.updated, UTC)

    @before_event([Insert])
    def set_created(self):
        self.created = int(datetime.now(UTC).timestamp())

    @before_event([Insert, Update, Replace])
    def set_updated(self):
        self.updated = int(datetime.now(UTC).timestamp())

    @property
    def mod_hashes(self):
        return [mod.hash for mod in self.mods]
