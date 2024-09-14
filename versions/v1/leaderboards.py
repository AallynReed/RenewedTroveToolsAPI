from quart import Blueprint, request, abort, current_app, Response
from .models.database.leaderboards import (
    Leaderboard,
    LeaderboardEntry,
    LeaderboardType,
    Contest,
    LeaderboardEntryArchive,
)
from utils import render_json
import re
import os
import asyncio
from .utils.discord import send_embed
from datetime import datetime, UTC, timedelta
from beanie import BulkWriter
from aiohttp import ClientSession
from hashlib import sha1
import json
from utils import Event, EventType


leaderboards = Blueprint("leaderboards", __name__, url_prefix="/leaderboards")


@leaderboards.route("/entries", methods=["GET"])
async def get_entries():
    params = request.args
    uuid = params.get("uuid", None)
    created_at = int(params.get("created_at", 0)) or None
    if not all([uuid, created_at]):
        return abort(400, "Missing uuid or created_at.")
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
        created_at = int(created_at_parse.timestamp())
    limit = int(params.get("limit", 0)) or None
    offset = int(params.get("offset", 0))
    pipeline = [
        {
            "$match": {
                "$and": [
                    {"leaderboard": int(uuid)},
                    {"created_at": created_at},
                ]
            }
        },
        {"$sort": {"rank": 1}},
        {
            "$project": {
                "_id": 0,
                "created_at": 0,
                "leaderboard": 0,
            }
        },
        *([{"$skip": offset}] if offset else []),
        *([{"$limit": limit}] if limit else []),
    ]
    pipeline_id = (
        f"leaderboard_search_{created_at}"
        + sha1(json.dumps(pipeline).encode()).hexdigest()
    )
    entries = await current_app.redis.get_object(pipeline_id)
    if entries:
        print("Cache hit")
        return Response(json.dumps(entries), content_type="application/json")
    final_query = LeaderboardEntry.aggregate(pipeline)
    entries = await final_query.to_list()
    await current_app.redis.set_object(pipeline_id, entries)
    await current_app.redis.expire(pipeline_id, 3600)
    response = Response(json.dumps(entries), content_type="application/json")
    return response


@leaderboards.route("/list", methods=["GET"])
async def get_list():
    params = request.args
    created_at = int(params.get("created_at", 0)) or None
    if created_at is None:
        return abort(400, "Missing created_at.")
    uuids = await LeaderboardEntry.distinct("leaderboard", {"created_at": created_at})
    items = await Leaderboard.find({"uuid": {"$in": uuids}}).to_list()
    json_items = []
    for item in items:
        json_item = item.model_dump(exclude=["id"])
        json_item["contest_type"] = None
        for contest in item.contests:
            if contest.time == created_at:
                json_item["contest_type"] = contest.type.name
        json_items.append(json_item)
    return render_json(json_items)


async def archive_entries(submit_time):
    delete_time = submit_time - timedelta(days=7)
    old_entries = LeaderboardEntry.find(
        {"created_at": {"$lt": delete_time.timestamp()}}
    )
    limit = 50000
    offset = 0
    while True:
        print(f"Archiving {offset} to {offset + limit}...")
        entries = await old_entries.skip(offset).limit(limit).to_list()
        offset += limit
        if not entries:
            break
        async with BulkWriter() as bw:
            for entry in entries:
                await LeaderboardEntryArchive.insert_one(
                    document=LeaderboardEntryArchive(
                        player_name=entry.player_name,
                        rank=entry.rank,
                        score=entry.score,
                        leaderboard=entry.leaderboard,
                        created_at=entry.created_at,
                    ),
                    bulk_writer=bw,
                )
    await LeaderboardEntry.find(
        {"created_at": {"$lt": delete_time.timestamp()}}
    ).delete_many()
    print("Done archiving.")


async def precache_entries(created_at, ts_date, missing=False):
    query = {"created_at": created_at}
    uuids = await LeaderboardEntry.distinct("leaderboard", query)
    offset = 0
    limit = None
    for i, uuid in enumerate(uuids):
        print(f"Precaching {i+1}/{len(uuids)}...")
        pipeline = [
            {
                "$match": {
                    "$and": [
                        {"leaderboard": uuid},
                        {"created_at": created_at},
                    ]
                }
            },
            {"$sort": {"rank": 1}},
            {
                "$project": {
                    "_id": 0,
                    "created_at": 0,
                    "leaderboard": 0,
                }
            },
            *([{"$skip": offset}] if offset else []),
            *([{"$limit": limit}] if limit else []),
        ]
        pipeline_id = (
            f"leaderboard_search_{created_at}"
            + sha1(json.dumps(pipeline).encode()).hexdigest()
        )
        final_query = LeaderboardEntry.aggregate(pipeline)
        entries = await final_query.to_list()
        await current_app.redis.set_object(pipeline_id, entries)
        await current_app.redis.expire(pipeline_id, 3600 * 24)
    async with ClientSession() as session:
        await session.get(
            f"https://trovesaurus.com/leaderboards/?import&key={os.getenv('TROVESAURUS_MARKET_TOKEN')}&day={ts_date}"
        )
    if not missing:
        await current_app.redis.publish_event(
            Event(
                id=created_at,
                type=EventType.leaderboards,
                data={"imported_at": created_at},
            )
        )
    print(f"Precached {len(uuids)} leaderboards for {ts_date}.")


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


async def insert_leaderboard_data(raw_data, missing=False):
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
    submit_time = raw_data.get("timestamp", submit_time)
    leaderboard_data = leaderboard_regex.findall(data)
    leaderboard_data.sort(
        key=lambda x: (int(x[1].startswith("Leaderboard_Category_Contests")), int(x[2]))
    )
    read_leaderboards = []
    for (
        leaderboard_id,
        category_id,
        uuid,
        name,
        category,
        raw_entries,
    ) in leaderboard_data:
        if category.upper() == "FAVORITES":
            continue
        leaderboards_imported += 1
        uuid = int(uuid)
        lb = await Leaderboard.find_one({"uuid": uuid})
        if lb is None:
            lb = await Leaderboard(
                uuid=uuid,
                name_id=leaderboard_id,
                name=name,
                category_id=category_id,
                category=category,
            ).save()
        lb_type = LeaderboardType.from_string(category_id)
        if lb_type != LeaderboardType.DEFAULT:
            contest = Contest(time=submit_time, type=lb_type)
            if contest.time not in [c.time for c in lb.contests]:
                lb.contests.append(contest)
                await lb.save()
        if uuid not in read_leaderboards:
            read_leaderboards.append(uuid)
            async with BulkWriter() as bw:
                for rank, player_name, score in entry_regex.findall(
                    "\n".join(raw_entries.split("|"))
                ):
                    await LeaderboardEntry.insert_one(
                        document=LeaderboardEntry(
                            player_name=player_name,
                            rank=int(rank),
                            score=float(score),
                            leaderboard=lb.uuid,
                            created_at=submit_time,
                        ),
                        bulk_writer=bw,
                    )
    submit_time = datetime.fromtimestamp(submit_time, UTC)
    asyncio.create_task(archive_entries(submit_time))
    year = submit_time.year
    day = submit_time.timetuple().tm_yday
    ts_date = f"{year}{day}"
    await send_embed(
        os.getenv("LEADERBOARD_WEBHOOK"),
        {
            "title": "Leaderboard Data inserted",
            "description": (f"{leaderboards_imported} leaderboards were submitted."),
            "color": 0x00FF00,
        },
    )
    await precache_entries(int(submit_time.timestamp()), ts_date, missing)


@leaderboards.route("/insert", methods=["POST"])
async def insert_entries():
    raw_data = await request.form
    if raw_data.get("Token") != os.getenv("TOKEN"):
        return abort(401)
    asyncio.create_task(insert_leaderboard_data(raw_data))
    return "OK", 200


async def insert_missing_data(data_blocks):
    for data in data_blocks:
        await insert_leaderboard_data(data, True)


@leaderboards.route("/insert_missing", methods=["GET", "POST"])
async def insert_missing_leaderboards():
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
    data_blocks = []
    for file in files.getlist("files[]"):
        timestamp = int(file.filename.split(".")[0])
        time = datetime.fromtimestamp(timestamp, UTC)
        time = int(
            time.replace(hour=11, minute=0, second=0, microsecond=0).timestamp() - 86400
        )
        data = {"timestamp": time, "data": file.read().decode("utf-8")}
        data_blocks.append(data)
    asyncio.create_task(insert_missing_data(data_blocks))
    return "OK", 200
