from beanie import Document, Indexed
from pydantic import Field, computed_field
from uuid import uuid4
from uuid import UUID
from typing import Optional
from datetime import datetime, UTC, timedelta


class MarketListing(Document):
    id: UUID = Field(default_factory=uuid4, alias="_id", unique=True)
    name: str
    type: Optional[str] = None
    stack: int
    price: int
    last_seen: int

    @computed_field
    @property
    def created_at(self) -> int:
        uuid_int = self.id.int
        time_low = uuid_int >> 96
        time_mid = (uuid_int >> 80) & 0xFFFF
        time_hi_and_version = (uuid_int >> 64) & 0xFFFF
        time_hi = time_hi_and_version & 0x0FFF
        timestamp = (time_hi << 48) | (time_mid << 32) | time_low
        uuid_epoch = datetime(1582, 10, 15)
        hundred_ns_intervals = timestamp
        timedelta_since_epoch = timedelta(microseconds=hundred_ns_intervals / 10)
        actual_datetime = uuid_epoch + timedelta_since_epoch
        return int(actual_datetime.timestamp())

    @computed_field
    @property
    def price_each(self) -> float:
        return round(self.price / self.stack, 3)

    @computed_field
    @property
    def expires_at(self) -> int:
        return self.created_at + 86400 * 7

    @computed_field
    @property
    def expired(self) -> bool:
        now = datetime.now(UTC).timestamp()
        return (now - self.created_at > 86400 * 7) or (now - self.last_seen > 3600 * 3)
