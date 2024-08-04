from quart import Blueprint, request, abort, current_app, send_file, Response
from .models.database.market import MarketListing
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
import numpy as np
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO


data_path = Path("versions/v1/data")

market = Blueprint("market", __name__, url_prefix="/market")


@market.route("/listings", methods=["GET"])
async def get_listings():
    params = request.args
    query = params.get("item", None)
    price_min = max(float(params.get("price_min", 0)), 0) or None
    price_max = max(float(params.get("price_max", 0)), 0) or None
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
    limit = int(params.get("limit", 0)) or None
    offset = int(params.get("offset", 0))
    query_dump = {}
    if query or price_min or price_max or created_before or created_after or last_seen_before or last_seen_after:
        query_dump = {
            "$and": [
                *(
                    [
                        {{"name": query}}
                    ] if query else []
                ),
                *([{"price": {"$lte": price_max}}] if price_max else []),
                *([{"price": {"$gte": price_min}}] if price_min else []),
                *([{"created_at": {"$lt": created_before}}] if created_before else []),
                *([{"created_at": {"$gt": created_after}}] if created_after else []),
                *([{"last_seen": {"$lt": last_seen_before}}] if last_seen_before else []),
                *([{"last_seen": {"$gt": last_seen_after}}] if last_seen_after else []),
            ]
        }
    final_query = MarketListing.find(query_dump)
    listings = await final_query.skip(offset).limit(limit).to_list()
    listings_count = await final_query.count()
    response = render_json([i.model_dump() for i in listings])
    response.headers["count"] = listings_count
    return response

@market.route("/interest_items", methods=["GET"])
async def get_interest_items():
    items = json.loads(data_path.joinpath("market_items.json").read_text())
    return render_json(sorted(items))

@market.route("/available_items", methods=["GET"])
async def get_items():
    items = await MarketListing.distinct("name")
    response = render_json(items)
    response.headers["count"] = len(items)
    return response

async def insert_market_data(raw_data):
    listings = []
    listing_regex = re.compile(r"([a-zA-Z0-9-]{36});([^;]+);([^;]*);(\d{1,4});(\d{1,8})", re.MULTILINE)
    now = int(datetime.now(UTC).timestamp())
    interest_items = json.loads(data_path.joinpath("market_items.json").read_text())
    result_listings = listing_regex.findall(raw_data.get("data", ""))
    imported = len(result_listings)
    for raw_uuid, name, type, stack, price in result_listings:
        if int(price) > 50_000_000:
            continue
        if name in interest_items:
            listings.append(
                MarketListing(
                    id=UUID(raw_uuid),
                    name=name,
                    type=type or None,
                    stack=int(stack),
                    price=int(price),
                    last_seen=now, 
                )
            )
        else:
            imported -= 1
    async with BulkWriter() as bw:
        for listing in listings:
            await MarketListing \
                .find_one({"_id": listing.id}, bulk_writer=bw) \
                .update_one(
                    {"$set": {"last_seen": listing.last_seen}},
                    {"$setOnInsert": listing.dict(include=["_id", "name", "type", "stack", "price"])},
                    upsert=True, bulk_writer=bw
                )
    async with ClientSession() as session:
        await session.get(f"https://trovesaurus.com/market?update&key={os.getenv('TROVESAURUS_MARKET_TOKEN')}")
    await send_embed(
        os.getenv("MARKET_WEBHOOK"),
        {
            "title": "Market Data inserted",
            "description": (
                f"{imported} listings were submitted."
            ),
            "color": 0x00FF00,
        },
    )

@market.route("/insert", methods=["POST"])
async def insert_listings():
    raw_data = await request.form
    if raw_data.get("Token") != os.getenv("TOKEN"):
        return abort(401)
    asyncio.create_task(insert_market_data(raw_data))
    return "OK", 200

### Statistical

@market.route("/hourly", methods=["GET"])
async def get_last_hour():
    raw_data = request.args
    try:
        item = raw_data["item"]
    except KeyError:
        return abort(400, "Missing Item")
    no_listings = "no_listings" in raw_data
    days = int(raw_data.get("days", 0))
    hours = int(raw_data.get("hours", 1))
    now = datetime.now(UTC)
    current_capture = now - timedelta(days=days, hours=hours)
    capture = []
    while current_capture < now:
        captured_listings = await MarketListing.find(
            {
                "$and": [
                    {"name": item},
                    {"last_seen": {"$gt": current_capture.timestamp()}}
                    ["created_at": {"$lt": (current_capture + timedelta(hours=1)).timestamp()}]
                ]
            }
        ).to_list()
        if not captured_listings:
            candidate = {
                "start": int(current_capture.timestamp()),
                "end": int((current_capture + timedelta(seconds=3599)).timestamp()),
                "total_stack": 0,
                "absolute_min": 0,
                "absolute_max": 0,
                "absolute_average": 0,
                "iqr_min": 0,
                "iqr_max": 0,
                "iqr_average": 0,
                "listings": []
            }
            capture.append(candidate)
            current_capture += timedelta(hours=1)
            continue
        captured_listings.sort(key=lambda x: x.price_each)
        captured_listings = [l.model_dump() for l in captured_listings if l.created_at < int(current_capture.timestamp())]
        prices = np.array([l["price_each"] for l in captured_listings])
        Q1 = np.percentile(prices, 25)
        Q3 = np.percentile(prices, 75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        filtered_prices = prices[(prices >= lower_bound) & (prices <= upper_bound)]
        frequency = Counter(list(filtered_prices))
        # Calculate Weighed Average
        total_weight = sum(frequency.values())
        weighted_sum = sum([k * v for k, v in frequency.items()])
        weighted_average = weighted_sum / total_weight
        candidate = {
            "start": int(current_capture.timestamp()),
            "end": int((current_capture + timedelta(seconds=3599)).timestamp()),
            "total_stack": sum(l["stack"] for l in captured_listings),
            "absolute_min": min(prices),
            "absolute_max": max(prices),
            "absolute_average": round(np.average(prices), 3),
            "iqr_min": min(list(filtered_prices)),
            "iqr_max": max(list(filtered_prices)),
            "iqr_average": round(weighted_average, 3),
            "listings": []
        }
        if not no_listings:
            candidate["listings"] = captured_listings
        capture.append(candidate)
        current_capture += timedelta(hours=1)
    return render_json(sorted(capture, key=lambda x: x["start"]))

@market.route("/hourly_graph", methods=["GET"])
async def get_last_hour_graph():
    name = request.args.get("item")
    if not name:
        return abort(400, "Missing Item")
    hours = int(request.args.get("hours", 1))
    try:
        async with ClientSession() as session:
            async with session.get(
                f"https://kiwiapi.aallyn.xyz/v1/market/hourly?item={name}&hours={hours}&no_listings"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    times = [datetime.fromtimestamp(item["start"], UTC) for item in data]
                    iqr_avg = [item["iqr_average"] for item in data]
                    iqr_max = [item["iqr_max"] for item in data]
                    iqr_min = [item["iqr_min"] for item in data]
                    plt.style.use('dark_background')
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(times, iqr_max, label="IQR Max", marker="o", markeredgecolor='#555555', color='#d62728')
                    ax.plot(times, iqr_avg, label="IQR Average", marker="o", markeredgecolor='#555555', color='#1f77b4')
                    ax.plot(times, iqr_min, label="IQR Min", marker="o", markeredgecolor='#555555', color='#2ca02c') 
                    ax.set_ylabel("Flux EA")
                    ax.set_title(name)
                    ax.legend()
                    ax.grid(True, color='#555555')
                    ax.ticklabel_format(style="plain", axis="y")
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d %H:%M"))
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, color='#555555')
                    plt.setp(ax.yaxis.get_majorticklabels(), color='#555555')
                    for spine in ax.spines.values():
                        spine.set_edgecolor('#555555')
                    plt.tight_layout()
                    buf = BytesIO()
                    plt.savefig(buf, format="png")
                    buf.seek(0)
                    return await send_file(buf, mimetype="image/png")
    except:
        ...
    return abort(500, "Failed to fetch data")

@market.route("/daily", methods=["GET"])
async def get_last_day():
    raw_data = request.args
    try:
        item = raw_data["item"]
    except KeyError:
        return abort(400, "Missing Item")
    no_listings = "no_listings" in raw_data
    days = int(raw_data.get("days", 1))
    now = datetime.now(UTC)
    current_capture = now - timedelta(days=days)
    capture = []
    while current_capture < now:
        captured_listings = await MarketListing.find(
            {
                "$and": [
                    {"name": item},
                    {"last_seen": {"$gt": current_capture.timestamp()}}
                    ["created_at": {"$lt": (current_capture + timedelta(days=1)).timestamp()}]
                ]
            }
        ).to_list()
        if not captured_listings:
            candidate = {
                "start": int(current_capture.timestamp()),
                "end": int((current_capture + timedelta(seconds=86399)).timestamp()),
                "total_stack": 0,
                "absolute_min": 0,
                "absolute_max": 0,
                "absolute_average": 0,
                "iqr_min": 0,
                "iqr_max": 0,
                "iqr_average": 0,
                "listings": []
            }
            capture.append(candidate)
            current_capture += timedelta(days=1)
            continue
        captured_listings.sort(key=lambda x: x.price_each)
        captured_listings = [l.model_dump() for l in captured_listings if l.created_at < int(current_capture.timestamp())]
        prices = np.array([l["price_each"] for l in captured_listings])
        Q1 = np.percentile(prices, 25)
        Q3 = np.percentile(prices, 75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        filtered_prices = prices[(prices >= lower_bound) & (prices <= upper_bound)]
        frequency = Counter(list(filtered_prices))
        # Calculate Weighed Average
        total_weight = sum(frequency.values())
        weighted_sum = sum([k * v for k, v in frequency.items()])
        weighted_average = weighted_sum / total_weight
        candidate = {
            "start": int(current_capture.timestamp()),
            "end": int((current_capture + timedelta(seconds=86399)).timestamp()),
            "total_stack": sum(l["stack"] for l in captured_listings),
            "absolute_min": min(prices),
            "absolute_max": max(prices),
            "absolute_average": round(np.average(prices), 3),
            "iqr_min": min(list(filtered_prices)),
            "iqr_max": max(list(filtered_prices)),
            "iqr_average": round(weighted_average, 3),
            "listings": []
        }
        if not no_listings:
            candidate["listings"] = captured_listings
        capture.append(candidate)
        current_capture += timedelta(days=1)
    return render_json(sorted(capture, key=lambda x: x["start"]))

@market.route("/daily_graph", methods=["GET"])
async def get_last_daily_graph():
    name = request.args.get("item")
    if not name:
        return abort(400, "Missing Item")
    days = int(request.args.get("days", 1))
    try:
        async with ClientSession() as session:
            async with session.get(
                f"https://kiwiapi.aallyn.xyz/v1/market/daily?item={name}&days={days}&no_listings"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    times = [datetime.fromtimestamp(item["start"], UTC) for item in data]
                    iqr_avg = [item["iqr_average"] for item in data]
                    iqr_max = [item["iqr_max"] for item in data]
                    iqr_min = [item["iqr_min"] for item in data]
                    plt.style.use('dark_background')
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(times, iqr_max, label="IQR Max", marker="o", markeredgecolor='#555555', color='#d62728')
                    ax.plot(times, iqr_avg, label="IQR Average", marker="o", markeredgecolor='#555555', color='#1f77b4')
                    ax.plot(times, iqr_min, label="IQR Min", marker="o", markeredgecolor='#555555', color='#2ca02c') 
                    ax.set_ylabel("Flux EA")
                    ax.set_title(name)
                    ax.legend()
                    ax.grid(True, color='#555555')
                    ax.ticklabel_format(style="plain", axis="y")
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, color='#555555')
                    plt.setp(ax.yaxis.get_majorticklabels(), color='#555555')
                    for spine in ax.spines.values():
                        spine.set_edgecolor('#555555')
                    plt.tight_layout()
                    buf = BytesIO()
                    plt.savefig(buf, format="png")
                    buf.seek(0)
                    return await send_file(buf, mimetype="image/png")
    except:
        ...
    return abort(500, "Failed to fetch data")