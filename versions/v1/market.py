from quart import Blueprint, request, abort, current_app, send_file, Response
from .models.database.market import MarketItem, MarketListing
from pathlib import Path
from utils import render_json
from uuid import UUID
import json
from .utils.cache import SortOrder
import re
import os
from aiohttp import ClientSession
import asyncio
from .utils.discord import send_embed
from datetime import datetime, timedelta, UTC
from beanie import BulkWriter


data_path = Path("versions/v1/data")

market = Blueprint("market", __name__, url_prefix="/market")


@market.route("/listings", methods=["GET"])
async def get_listings():
    params = request.args
    query = params.get("item", None)
    items = [t.strip() for t in params.get("items", "").split(";") if t.strip()]
    type = params.get("type", None)
    types = [t.strip() for t in params.get("types", "").split(";") if t.strip()]
    price_min = max(int(params.get("price_min", 0)), 0) or None
    price_max = max(int(params.get("price_max", 0)), 0) or None
    created_before = int(params.get("created_before", 0)) or None
    created_after = int(params.get("created_after", 0)) or None
    last_seen_before = int(params.get("last_seen_before", 0)) or None
    last_seen_after = int(params.get("last_seen_after", 0)) or None
    if price_min and price_max and price_min > price_max:
        return abort(400, "\"price_min\" can't be greater than \"price_max\"")
    if created_before and created_after and created_before < created_after:
        return abort(400, "\"created_before\" can't be less than \"created_after\"")
    if last_seen_before and last_seen_after and last_seen_before < last_seen_after:
        return abort(400, "\"last_seen_before\" can't be less than \"last_seen_after\"")
    price_ord = params.get("price_ord", None)
    if price_ord is not None and price_ord not in ["asc", "desc"]:
        return abort(400, "\"price_ord\" parameter got the wrong value, valid inputs are \"asc\", \"desc\"")
    limit = int(params.get("limit", 0)) or None
    offset = int(params.get("offset", 0))
    query_dump = {}
    if query or items or type or types or price_min or price_max or created_before or created_after or last_seen_before or last_seen_after:
        query_dump = {
            "$and": [
                *(
                    [
                        {
                            "$or": [
                                *(
                                    [
                                        {"name": {"$regex": "^" + query + "$"}}
                                        if query is not None else
                                        {"name": {"$in": items}}
                                    ] if query or items else []
                                ),
                                *(
                                    [
                                        {"type": {"$regex": "^" + type + "$"}}
                                        if query is not None else
                                        {"type": {"$in": types}}
                                    ] if type or types else []
                                )
                            ]
                        }
                    ] if query or items or type or types else []
                ),
                *([{"price": {"$lte": price_max}}] if price_max else []),
                *([{"price": {"$gte": price_min}}] if price_min else []),
                *([{"created_at": {"$lt": created_before}}] if created_before else []),
                *([{"created_at": {"$gt": created_after}}] if created_after else []),
                *([{"last_seen": {"$lt": last_seen_before}}] if last_seen_before else []),
                *([{"last_seen": {"$gt": last_seen_after}}] if last_seen_after else []),
            ]
        }
    sort_by = [
        *(
            [
                ("price", price_ord)
            ]
            if price_ord is not None else []
        )
    ]
    final_query = MarketListing.find(query_dump).sort(sort_by)
    listings = await final_query.skip(offset).limit(limit).to_list()
    listings_count = await final_query.count()
    response = render_json([i.model_dump() for i in listings])
    response.headers["count"] = listings_count
    return response

@market.route("/interest_items", methods=["GET"])
async def get_interest_items():
    items = json.loads(data_path.joinpath("market_items.json").read_text())
    return render_json(items)

@market.route("/available_items", methods=["GET"])
async def get_items():
    items = await MarketItem.distinct("name")
    return render_json(items)

@market.route("/types", methods=["GET"])
async def get_types():
    items = await MarketItem.distinct("type")
    return render_json(items)

async def insert_data(raw_data):
    listings = []
    listing_regex = re.compile(r"([a-zA-Z0-9-]{36});(.+?);(.*?);(\d+);(\d+)", re.MULTILINE)
    now = int(datetime.now(UTC).timestamp())
    interest_items = json.loads(data_path.joinpath("market_items.json").read_text())
    for line in raw_data.get("data", "").splitlines():
        if line.startswith("listings = "):
            raw_data_line = line[11:].strip()
            raw_listings = raw_data_line.replace("|", "\n")
            result_listings = listing_regex.findall(raw_listings)
            for raw_uuid, name, type, size, price in result_listings:
                if name in interest_items:
                    listings.append(
                        MarketListing(
                            id=UUID(raw_uuid),
                            name=name,
                            type=type or None,
                            size=size,
                            price=price,
                            last_seen=now, 
                        )
                    )
    async with BulkWriter() as bw:
        for listing in listings:
            await MarketListing \
                .find_one({"_id": listing.id}, bulk_writer=bw) \
                .upsert({"$set": {"last_seen": listing.last_seen}}, on_insert=listing, bulk_writer=bw)
    async with ClientSession() as session:
        await session.get(f"https://trovesaurus.com/market?update&key={os.getenv('TROVESAURUS_MARKET_TOKEN')}")
    await send_embed(
        os.getenv("MARKET_WEBHOOK"),
        {
            "title": "Market Data inserted",
            "description": (
                f"{len(result_listings)} listings were submitted."
            ),
            "color": 0x00FF00,
        },
    )

@market.route("/insert", methods=["POST"])
async def insert_listings():
    raw_data = await request.form
    if raw_data.get("Token") != os.getenv("TOKEN"):
        return abort(401)
    asyncio.create_task(insert_data(raw_data))
    return "OK", 200


### Statistical

@market.route("/last_hour", methods=["GET"])
async def get_last_hour():
    last_hour_listings = await MarketListing.find(
        MarketListing.last_seen > (datetime.now() - timedelta(hours=1)).timestamp()
    ).to_list()
    previous_hour_listings = await MarketListing.find(
        MarketListing.last_seen > (datetime.now() - timedelta(hours=2)).timestamp() and
        MarketListing.created_at < (datetime.now() - timedelta(hours=1)).timestamp()
    ).to_list()
    last_hour_items = {
        listing.name: [listing.price_each for listing in last_hour_listings]
        for listing in last_hour_listings
    }
    previous_hour_items = {
        listing.name: [listing.price_each for listing in previous_hour_listings]
        for listing in previous_hour_listings
    }
    return "OK", 200