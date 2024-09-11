from quart import Blueprint, request, abort, send_file, current_app
from .models.database.market import MarketListing, MarketCapture, get_capture_query
from pathlib import Path
from utils import render_json
from uuid import UUID
import json
import re
import os
from aiohttp import ClientSession
import asyncio
from .utils.discord import send_embed
from datetime import datetime, timedelta, UTC
from beanie import BulkWriter
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from io import BytesIO
from .utils.functions import intword
from utils import Event, EventType
from hashlib import sha1


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
        return abort(400, '"price_min" can\'t be greater than "price_max"')
    if created_before and created_after and created_before < created_after:
        return abort(400, '"created_before" can\'t be less than "created_after"')
    if last_seen_before and last_seen_after and last_seen_before < last_seen_after:
        return abort(400, '"last_seen_before" can\'t be less than "last_seen_after"')
    limit = int(params.get("limit", 0)) or None
    offset = int(params.get("offset", 0))
    query_dump = {}
    if (
        query
        or price_min
        or price_max
        or created_before
        or created_after
        or last_seen_before
        or last_seen_after
    ):
        query_dump = {
            "$and": [
                *([{"name": query}] if query else []),
                *([{"price": {"$lte": price_max}}] if price_max else []),
                *([{"price": {"$gte": price_min}}] if price_min else []),
                *([{"created_at": {"$lt": created_before}}] if created_before else []),
                *([{"created_at": {"$gt": created_after}}] if created_after else []),
                *(
                    [{"last_seen": {"$lt": last_seen_before}}]
                    if last_seen_before
                    else []
                ),
                *(
                    [{"last_seen": {"$gte": last_seen_after}}]
                    if last_seen_after
                    else []
                ),
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
    listing_regex = re.compile(
        r"([a-zA-Z0-9-]{36});([^;]+);([^;]*);(\d{1,4});(\d{1,8})", re.MULTILINE
    )
    now = int(datetime.now(UTC).replace(second=0, microsecond=0).timestamp())
    now = raw_data.get("timestamp", now)
    interest_items = json.loads(data_path.joinpath("market_items.json").read_text())
    result_listings = listing_regex.findall(raw_data.get("data", ""))
    imported = len(result_listings)
    for raw_uuid, name, type, stack, price in result_listings:
        if int(price) > 50_000_000:
            continue
        if name in interest_items:
            uuid = UUID(raw_uuid)
            listings.append(
                MarketListing(
                    id=uuid,
                    name=name,
                    type=type or None,
                    stack=int(stack),
                    price=int(price),
                    price_each=round(int(price) / int(stack), 3),
                    last_seen=now,
                    created_at=int(
                        (
                            datetime(1582, 10, 15)
                            + timedelta(microseconds=uuid.time / 10)
                        )
                        .replace(microsecond=0)
                        .timestamp()
                    ),
                )
            )
        else:
            imported -= 1
    async with BulkWriter() as bw:
        for listing in listings:
            await MarketListing.find_one(
                {"_id": listing.id}, bulk_writer=bw
            ).update_one(
                {"$set": {"last_seen": listing.last_seen}},
                {
                    "$setOnInsert": listing.dict(
                        include=[
                            "_id",
                            "name",
                            "type",
                            "stack",
                            "price",
                            "created_at",
                            "price_each",
                        ]
                    )
                },
                upsert=True,
                bulk_writer=bw,
            )
    async with ClientSession() as session:
        await session.get(
            f"https://trovesaurus.com/market?update&key={os.getenv('TROVESAURUS_MARKET_TOKEN')}&last_seen_after={now}"
        )
    await current_app.redis.publish_event(
        Event(id=int(now), type=EventType.market, data={"imported_at": now})
    )
    await send_embed(
        os.getenv("MARKET_WEBHOOK"),
        {
            "title": "Market Data inserted",
            "description": (f"{imported} listings were submitted."),
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


async def insert_missing_market_data(files):
    await asyncio.sleep(3)
    for filename, content in files:
        timestamp = int(filename.split(".")[0])
        time = datetime.fromtimestamp(timestamp, UTC)
        time = int(time.replace(second=0, microsecond=0).timestamp())
        data = {"timestamp": time, "data": content}
        await insert_market_data(data)


@market.route("/insert_missing", methods=["GET", "POST"])
async def insert_missing_market():
    if request.method == "GET":
        return """
        <form method="post" enctype="multipart/form-data">
            <input type="text" name="password">
            <input type="file" name="files[]" multiple>
            <input type="submit">
        </form>
        """

    files = await request.files
    if "files[]" not in files:
        return abort(400)
    read_files = [
        (f.filename, f.read().decode("utf-8")) for f in files.getlist("files[]")
    ]
    asyncio.create_task(insert_missing_market_data(read_files))
    return "OK", 200


# async def cache_missing_trovesaurus():
#     await asyncio.sleep(3)
#     raw_data = open("missing.txt", "r").read()
#     listing_uuids = {l.strip():"" for l in raw_data.splitlines() if l.strip()}
#     documents = []
#     i =0
#     async for doc in MarketListing.find():
#         if str(doc.id) in listing_uuids:
#             continue
#         i += 1
#         print(i)
#         documents.append(doc)
#     await current_app.redis.set_object("trovesaurus_missing_market", [i.model_dump() for i in documents])
#     await current_app.redis.expire("trovesaurus_missing_market", 3600)
#     print("Done")


# @market.route("/trovesaurus_missing")
# async def trovesaurus_missing():
#     data = await current_app.redis.get_object("trovesaurus_missing_market")
#     if data is None:
#         asyncio.create_task(cache_missing_trovesaurus())
#         return "OK", 200
#     return render_json(data)


### Statistical


async def clear_old_market_searches():
    last_listing = await MarketListing.find_one({}, sort=[("last_seen", -1)])
    if last_listing:
        last_seen = last_listing.last_seen
        async for key in current_app.redis.scan_iter("market_search_*"):
            timestamp = int(key.decode("utf-8").split("_")[-2])
            if timestamp != last_seen:
                await current_app.redis.delete(key)


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
    last_listing = await MarketListing.find_one({}, sort=[("last_seen", -1)])
    meshed_search = (
        f"market_search_{last_listing.last_seen}_"
        + sha1(f"{item}{days}{hours}{int(no_listings)}".encode()).hexdigest()
    )
    await clear_old_market_searches()
    data = await current_app.redis.get_object(meshed_search)
    if data is None:
        now = datetime.fromtimestamp(last_listing.last_seen, UTC)
        current_capture = now - timedelta(days=days, hours=hours, minutes=-2)
        capture = []
        while current_capture < now:
            start = int(current_capture.timestamp())
            end = int((current_capture + timedelta(hours=1, seconds=-1)).timestamp())
            captured_listings = (
                await MarketListing.find({})
                .aggregate(get_capture_query(item, start, end))
                .to_list()
            )
            capture.append(captured_listings[0])
            current_capture += timedelta(hours=1)
        data = sorted(capture, key=lambda x: x["start"])
        await current_app.redis.set_object(meshed_search, data)
    return render_json(data)


@market.route("/hourly_graph", methods=["GET"])
async def get_last_hour_graph():
    name = request.args.get("item")
    if not name:
        return abort(400, "Missing Item")
    hours = int(request.args.get("hours", 1))
    days = int(request.args.get("days", 0))
    last_listing = await MarketListing.find_one({}, sort=[("last_seen", -1)])
    meshed_search = (
        f"market_search_graph_{last_listing.last_seen}_"
        + sha1(f"{name}{days}{hours}".encode()).hexdigest()
    )
    await clear_old_market_searches()
    data = await current_app.redis.get(meshed_search)
    if data is not None:
        return await send_file(BytesIO(data), mimetype="image/png")
    try:
        async with ClientSession() as session:
            async with session.get(
                f"https://kiwiapi.aallyn.xyz/v1/market/hourly?item={name}&hours={hours}&days={days}&no_listings"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    times = [
                        datetime.fromtimestamp(item["start"], UTC) for item in data
                    ]
                    iqr_avg = [item["iqr_avg"] for item in data]
                    iqr_max = [item["iqr_max"] for item in data]
                    iqr_min = [item["iqr_min"] for item in data]
                    plt.style.use("dark_background")
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(
                        times,
                        iqr_max,
                        label="IQR Max",
                        marker="o",
                        markeredgecolor="#555555",
                        color="#d62728",
                    )
                    ax.plot(
                        times,
                        iqr_avg,
                        label="IQR Average",
                        marker="o",
                        markeredgecolor="#555555",
                        color="#1f77b4",
                    )
                    ax.plot(
                        times,
                        iqr_min,
                        label="IQR Min",
                        marker="o",
                        markeredgecolor="#555555",
                        color="#2ca02c",
                    )
                    ax.set_ylim(ymin=0)
                    ax.set_ylabel("Flux EA")
                    ax.set_title(name)
                    ax.legend()
                    ax.grid(True, color="#555555")
                    ax.ticklabel_format(style="plain", axis="y")
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d %H:%M"))
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
                    plt.setp(
                        ax.xaxis.get_majorticklabels(), rotation=45, color="#555555"
                    )
                    plt.setp(ax.yaxis.get_majorticklabels(), color="#555555")
                    for spine in ax.spines.values():
                        spine.set_edgecolor("#555555")
                    plt.tight_layout()
                    buf = BytesIO()
                    plt.savefig(buf, format="png")
                    buf.seek(0)
                    await current_app.redis.set(meshed_search, buf.getvalue())
                    return await send_file(buf, mimetype="image/png")
    except:
        ...
    return abort(500, "Failed to fetch data")


@market.route("/hourly_market_flux", methods=["GET"])
async def get_last_hour_market_flux():
    raw_data = request.args
    days = int(raw_data.get("days", 0))
    hours = int(raw_data.get("hours", 1))
    last_listing = await MarketListing.find_one({}, sort=[("last_seen", -1)])
    now = datetime.fromtimestamp(last_listing.last_seen, UTC)
    current_capture = now - timedelta(days=days, hours=hours, minutes=-2)
    capture = []
    while current_capture < now:
        start = int(current_capture.timestamp())
        end = int((current_capture + timedelta(seconds=3599)).timestamp())
        captured_listings = (
            await MarketListing.find()
            .aggregate(
                [
                    {
                        "$match": {
                            "last_seen": {"$gt": start},
                            "created_at": {"$lt": end},
                        }
                    },
                    {"$group": {"_id": None, "total_flux": {"$sum": "$price"}}},
                ],
                projection_model=MarketCapture,
            )
            .to_list()
        )
        candidate = {
            "start": start,
            "end": end,
            "total_flux": captured_listings[0].total_flux,
        }
        capture.append(candidate)
        current_capture += timedelta(hours=1)
    return render_json(sorted(capture, key=lambda x: x["start"]))


@market.route("/hourly_market_flux_graph", methods=["GET"])
async def get_last_hour_market_flux_graph():
    hours = int(request.args.get("hours", 1))
    days = int(request.args.get("days", 0))
    try:
        async with ClientSession() as session:
            async with session.get(
                f"https://kiwiapi.aallyn.xyz/v1/market/hourly_market_flux?hours={hours}&days={days}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    times = [
                        datetime.fromtimestamp(item["start"], UTC) for item in data
                    ]
                    total_flux = [item["total_flux"] for item in data]
                    plt.style.use("dark_background")
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(
                        times,
                        total_flux,
                        label="Total Flux",
                        marker="o",
                        markeredgecolor="#555555",
                        color="#d62728",
                    )
                    ax.set_ylim(ymin=0)
                    ax.set_ylabel("Total Flux")
                    ax.set_title("Total Market Flux")
                    ax.legend()
                    ax.grid(True, color="#555555")
                    ax.ticklabel_format(style="plain", axis="y")
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d %H:%M"))
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: intword(x)))
                    plt.setp(
                        ax.xaxis.get_majorticklabels(), rotation=45, color="#555555"
                    )
                    plt.setp(ax.yaxis.get_majorticklabels(), color="#555555")
                    for spine in ax.spines.values():
                        spine.set_edgecolor("#555555")
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
    last_listing = await MarketListing.find_one({}, sort=[("last_seen", -1)])
    meshed_search = (
        f"market_search_{last_listing.last_seen}_"
        + sha1(f"{item}{days}{int(no_listings)}".encode()).hexdigest()
    )
    await clear_old_market_searches()
    data = await current_app.redis.get_object(meshed_search)
    if data is None:
        now = datetime.fromtimestamp(last_listing.last_seen, UTC)
        current_capture = now - timedelta(days=days, minutes=-2)
        capture = []
        while current_capture < now:
            start = int(current_capture.timestamp())
            end = int((current_capture + timedelta(days=1, seconds=-1)).timestamp())
            captured_listings = (
                await MarketListing.find({})
                .aggregate(get_capture_query(item, start, end))
                .to_list()
            )
            capture.append(captured_listings[0])
            current_capture += timedelta(days=1)
        data = sorted(capture, key=lambda x: x["start"])
        await current_app.redis.set_object(meshed_search, data)
    return render_json(data)


@market.route("/daily_graph", methods=["GET"])
async def get_last_daily_graph():
    name = request.args.get("item")
    if not name:
        return abort(400, "Missing Item")
    last_listing = await MarketListing.find_one({}, sort=[("last_seen", -1)])
    days = int(request.args.get("days", 1))
    meshed_search = (
        f"market_search_graph_{last_listing.last_seen}_"
        + sha1(f"{name}{days}".encode()).hexdigest()
    )
    await clear_old_market_searches()
    data = await current_app.redis.get(meshed_search)
    if data is not None:
        return await send_file(BytesIO(data), mimetype="image/png")
    try:
        async with ClientSession() as session:
            async with session.get(
                f"https://kiwiapi.aallyn.xyz/v1/market/daily?item={name}&days={days}&no_listings"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    times = [
                        datetime.fromtimestamp(item["start"], UTC) for item in data
                    ]
                    iqr_avg = [item["iqr_avg"] for item in data]
                    iqr_max = [item["iqr_max"] for item in data]
                    iqr_min = [item["iqr_min"] for item in data]
                    plt.style.use("dark_background")
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(
                        times,
                        iqr_max,
                        label="IQR Max",
                        marker="o",
                        markeredgecolor="#555555",
                        color="#d62728",
                    )
                    ax.plot(
                        times,
                        iqr_avg,
                        label="IQR Average",
                        marker="o",
                        markeredgecolor="#555555",
                        color="#1f77b4",
                    )
                    ax.plot(
                        times,
                        iqr_min,
                        label="IQR Min",
                        marker="o",
                        markeredgecolor="#555555",
                        color="#2ca02c",
                    )
                    ax.set_ylim(ymin=0)
                    ax.set_ylabel("Flux EA")
                    ax.set_title(name)
                    ax.legend()
                    ax.grid(True, color="#555555")
                    ax.ticklabel_format(style="plain", axis="y")
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                    plt.setp(
                        ax.xaxis.get_majorticklabels(), rotation=45, color="#555555"
                    )
                    plt.setp(ax.yaxis.get_majorticklabels(), color="#555555")
                    for spine in ax.spines.values():
                        spine.set_edgecolor("#555555")
                    plt.tight_layout()
                    buf = BytesIO()
                    plt.savefig(buf, format="png")
                    buf.seek(0)
                    await current_app.redis.set(meshed_search, buf.getvalue())
                    return await send_file(buf, mimetype="image/png")
    except:
        ...
    return abort(500, "Failed to fetch data")


@market.route("/daily_market_flux", methods=["GET"])
async def get_last_day_market_flux():
    raw_data = request.args
    days = int(raw_data.get("days", 1))
    last_listing = await MarketListing.find_one({}, sort=[("last_seen", -1)])
    now = datetime.fromtimestamp(last_listing.last_seen, UTC)
    current_capture = now - timedelta(days=days, minutes=-2)
    capture = []
    while current_capture < now:
        captured_listings = (
            await MarketListing.find()
            .aggregate(
                [
                    {
                        "$match": {
                            "last_seen": {"$gt": int(current_capture.timestamp())},
                            "created_at": {"$lt": int(current_capture.timestamp())},
                        }
                    },
                    {"$group": {"_id": None, "total_flux": {"$sum": "$price"}}},
                ],
                projection_model=MarketCapture,
            )
            .to_list()
        )
        candidate = {
            "start": int(current_capture.timestamp()),
            "end": int((current_capture + timedelta(seconds=86399)).timestamp()),
            "total_flux": captured_listings[0].total_flux,
        }
        capture.append(candidate)
        current_capture += timedelta(days=1)
    return render_json(sorted(capture, key=lambda x: x["start"]))


@market.route("/daily_market_flux_graph", methods=["GET"])
async def get_last_day_market_flux_graph():
    days = int(request.args.get("days", 0))
    try:
        async with ClientSession() as session:
            async with session.get(
                f"https://kiwiapi.aallyn.xyz/v1/market/daily_market_flux?days={days}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    times = [
                        datetime.fromtimestamp(item["start"], UTC) for item in data
                    ]
                    total_flux = [item["total_flux"] for item in data]
                    plt.style.use("dark_background")
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.plot(
                        times,
                        total_flux,
                        label="Total Flux",
                        marker="o",
                        markeredgecolor="#555555",
                        color="#d62728",
                    )
                    ax.set_ylim(ymin=0)
                    ax.set_ylabel("Total Flux")
                    ax.set_title("Total Market Flux")
                    ax.legend()
                    ax.grid(True, color="#555555")
                    ax.ticklabel_format(style="plain", axis="y")
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: intword(x)))
                    plt.setp(
                        ax.xaxis.get_majorticklabels(), rotation=45, color="#555555"
                    )
                    plt.setp(ax.yaxis.get_majorticklabels(), color="#555555")
                    for spine in ax.spines.values():
                        spine.set_edgecolor("#555555")
                    plt.tight_layout()
                    buf = BytesIO()
                    plt.savefig(buf, format="png")
                    buf.seek(0)
                    return await send_file(buf, mimetype="image/png")
    except:
        ...
    return abort(500, "Failed to fetch data")
