from beanie import Document, Indexed
from pydantic import Field, computed_field, BaseModel
from uuid import uuid4
from uuid import UUID
from typing import Optional
from datetime import datetime, UTC, timedelta


class MarketListing(Document):
    id: UUID = Field(default_factory=uuid4, alias="_id", unique=True)
    name: Indexed(str)
    type: Optional[str] = None
    stack: int
    price: int
    price_each: Indexed(float)
    last_seen: Indexed(int)
    created_at: Indexed(int) = 0

    @computed_field
    @property
    def expires_at(self) -> int:
        return self.created_at + 86400 * 7

    @computed_field
    @property
    def expired(self) -> bool:
        now = datetime.now(UTC).timestamp()
        return (now - self.created_at > 86400 * 7) or (now - self.last_seen > 3600 * 3)


class MarketCapture(BaseModel):
    _id: Optional[str]
    total_flux: int


def get_capture_query(item, start, end):
    return [
        {
            "$match": {
                "name": item,
                "last_seen": {"$gt": start},
                "created_at": {"$lt": end},
            }
        },
        {"$sort": {"price_each": 1}},
        {
            "$group": {
                "_id": None,
                "allPrices": {
                    "$push": {
                        "price": "$price",
                        "price_each": "$price_each",
                        "stack": "$stack",
                    }
                },
                "absolute_min": {"$min": "$price_each"},
                "absolute_max": {"$max": "$price_each"},
                "total_price": {"$sum": "$price"},
                "total_stack": {"$sum": "$stack"},
            }
        },
        {
            "$project": {
                "total_price": 1,
                "total_stack": 1,
                "absolute_min": 1,
                "absolute_max": 1,
                "absolute_avg": {"$round": [{"$avg": "$allPrices.price_each"}, 3]},
                "count": {"$size": "$allPrices"},
                "q1": {
                    "$arrayElemAt": [
                        "$allPrices.price_each",
                        {
                            "$floor": {
                                "$multiply": [
                                    0.2,
                                    {"$subtract": [{"$size": "$allPrices"}, 1]},
                                ]
                            }
                        },
                    ]
                },
                "q3": {
                    "$arrayElemAt": [
                        "$allPrices.price_each",
                        {
                            "$floor": {
                                "$multiply": [
                                    0.8,
                                    {"$subtract": [{"$size": "$allPrices"}, 1]},
                                ]
                            }
                        },
                    ]
                },
            }
        },
        {"$addFields": {"iqr": {"$subtract": ["$q3", "$q1"]}}},
        {
            "$addFields": {
                "lower_bound": {"$subtract": ["$q1", {"$multiply": [1.3, "$iqr"]}]},
                "upper_bound": {"$add": ["$q3", {"$multiply": [1.3, "$iqr"]}]},
            }
        },
        {
            "$lookup": {
                "from": "MarketListing",
                "let": {"lower": "$lower_bound", "upper": "$upper_bound"},
                "pipeline": [
                    {
                        "$match": {
                            "name": item,
                            "last_seen": {"$gt": start},
                            "created_at": {"$lt": end},
                            "$expr": {
                                "$and": [
                                    {"$gte": ["$price_each", "$$lower"]},
                                    {"$lte": ["$price_each", "$$upper"]},
                                ]
                            },
                        }
                    },
                ],
                "as": "filteredPrices",
            }
        },
        {
            "$project": {
                "start": {"$toLong": start},
                "end": {"$toLong": end},
                "absolute_min": 1,
                "absolute_max": 1,
                "absolute_avg": 1,
                "total_price": 1,
                "total_stack": 1,
                "iqr_min": {"$min": "$filteredPrices.price_each"},
                "iqr_max": {"$max": "$filteredPrices.price_each"},
                "iqr_avg": {"$round": [{"$avg": "$filteredPrices.price_each"}, 3]},
            }
        },
    ]
