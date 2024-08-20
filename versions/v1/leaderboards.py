from quart import Blueprint, request, abort, current_app
from .models.database.leaderboards import LeaderboardEntry
from utils import render_json
import re
import os
import asyncio
from .utils.discord import send_embed
from datetime import datetime, UTC, timedelta
from beanie import BulkWriter
from aiohttp import ClientSession

leaderboards = Blueprint("leaderboards", __name__, url_prefix="/leaderboards")


@leaderboards.route("/entries", methods=["GET"])
async def get_entries():
    params = request.args
    query = params.get("name_id", None)
    category = params.get("category_id", None)
    with_count = int(params.get("with_count", 1))
    created_at = int(params.get("created_at", 0)) or None
    remove_fields = params.get("remove_fields", "")
    remove_fields = remove_fields.split(",") if remove_fields else []
    if created_at:
        created_at_parse = datetime.fromtimestamp(created_at, UTC).replace(
            minute=0, second=0
        )
        if created_at_parse.hour not in [0, 11]:
            return abort(
                400,
                "Invalid timestamp, please give either UTC midnight or 11am (Trove time).",
            )
        if created_at_parse.hour == 0:
            created_at_parse = created_at_parse.replace(hour=11)
        created_at = created_at_parse.timestamp()
    limit = int(params.get("limit", 0)) or None
    offset = int(params.get("offset", 0))
    query_dump = {}
    if query or created_at or category:
        query_dump = {
            "$and": [
                *([{"name_id": query}] if query else []),
                *([{"category_id": category}] if category else []),
                *([{"created_at": created_at}] if created_at else []),
            ]
        }
    final_query = LeaderboardEntry.find(query_dump).sort([("rank", 1)])
    entries = await final_query.skip(offset).limit(limit).to_list()
    response = render_json(
        [
            i.model_dump(
                exclude=["id"]
                + remove_fields
                + (["created_at"] if created_at else [])
                + (["name_id"] if query else [])
                + (["category_id"] if category else [])
            )
            for i in entries
        ]
    )
    if with_count:
        entries_count = await final_query.count()
        response.headers["count"] = entries_count
    return response


@leaderboards.route("/list", methods=["GET"])
async def get_list():
    params = request.args
    created_at = int(params.get("created_at", 0)) or None
    category = params.get("category_id", None)
    query = {}
    if created_at:
        query.update({"created_at": created_at})
    if category:
        query.update({"category_id": category})
    items = (
        await LeaderboardEntry.find(query)
        .aggregate(
            [
                {
                    "$group": {
                        "_id": {
                            "uuid": "$uuid",
                            "name_id": "$name_id",
                            "category_id": "$category_id",
                        },
                        "count": {"$sum": 1},
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "uuid": "$_id.uuid",
                        "name_id": "$_id.name_id",
                        "category_id": "$_id.category_id",
                        "count": 1,
                    }
                },
                {"$sort": {"uuid": 1, "name_id": 1, "category_id": 1}},
            ]
        )
        .to_list()
    )
    return render_json(items)


@leaderboards.route("/categories", methods=["GET"])
async def get_categories_list():
    params = request.args
    created_at = int(params.get("created_at", 0)) or None
    query = {}
    if created_at:
        query.update({"created_at": created_at})
    items = await LeaderboardEntry.distinct("category_id", query)
    response = render_json(items)
    response.headers["count"] = len(items)
    response.headers["total_entries"] = await LeaderboardEntry.find(query).count()
    return response


async def import_data():
    documents = []
    i = 0
    async for entry in current_app.database_client.trove_api[
        "LeaderboardEntryPort"
    ].find({}, {"_id": 0}):
        documents.append(
            LeaderboardEntry(
                uuid=entry["uuid"],
                name=entry["name"],
                name_id=entry["name_id"],
                category_id=entry["category_id"],
                category=entry["category"],
                player_name=entry["player_name"],
                rank=int(entry["rank"]),
                score=float(entry["score"]),
                created_at=entry["created_at"],
            )
        )
        i += 1
        if not i % 10000:
            await LeaderboardEntry.insert_many(documents)
            documents = []
            print(f"Inserted {i} entries.")
    await LeaderboardEntry.insert_many(documents)
    print(f"Inserted {i} entries.")
    print("Done.")


# @leaderboards.route("/import_data", methods=["GET"])
# async def get_category_names():
#     asyncio.create_task(import_data())
#     return "OK", 200


@leaderboards.route("/timestamps", methods=["GET"])
async def get_interest_items():
    timestamps = await LeaderboardEntry.distinct("created_at")
    return render_json(sorted(timestamps, reverse=True))


async def insert_leaderboard_data(raw_data):
    data = raw_data.get("data", "")
    leaderboard_regex = re.compile(
        r"^(.+?)\$(.+?)\$(\d+?) = (.+?)\$(.+?)##(.+)$", re.MULTILINE
    )
    entry_regex = re.compile(r"^(\d{1,4});([^;]+?);([^;]+?)$", re.MULTILINE)
    leaderboards_imported = 0
    submit_time = int(
        (
            datetime.now(UTC).replace(hour=11, minute=0, second=0, microsecond=0)
            - timedelta(days=1)
        ).timestamp()
    )
    for (
        leaderboard_id,
        category_id,
        uuid,
        name,
        category,
        raw_entries,
    ) in leaderboard_regex.findall(data):
        if category.upper() == "FAVORITES":
            continue
        leaderboards_imported += 1
        async with BulkWriter() as bw:
            for rank, player_name, score in entry_regex.findall(
                "\n".join(raw_entries.split("|"))
            ):
                await LeaderboardEntry.insert_one(
                    document=LeaderboardEntry(
                        uuid=int(uuid),
                        name=name,
                        name_id=leaderboard_id,
                        category_id=category_id,
                        category=category.upper() or "NULL",
                        player_name=player_name,
                        rank=int(rank),
                        score=float(score),
                        created_at=submit_time,
                    ),
                    bulk_writer=bw,
                )
    async with ClientSession() as session:
        await session.get(
            f"https://trovesaurus.com/leaderboards?update&key={os.getenv('TROVESAURUS_MARKET_TOKEN')}&timestamp={submit_time}"
        )
    await send_embed(
        os.getenv("LEADERBOARD_WEBHOOK"),
        {
            "title": "Leaderboard Data inserted",
            "description": (f"{leaderboards_imported} leaderboards were submitted."),
            "color": 0x00FF00,
        },
    )


@leaderboards.route("/insert", methods=["POST"])
async def insert_entries():
    raw_data = await request.form
    if raw_data.get("Token") != os.getenv("TOKEN"):
        return abort(401)
    asyncio.create_task(insert_leaderboard_data(raw_data))
    return "OK", 200
