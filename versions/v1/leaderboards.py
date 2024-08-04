from quart import Blueprint, request, abort
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
    query = params.get("leaderboard_id", None)
    created_at = int(params.get("created_at", 0)) or None
    if created_at:
        created_at_parse = datetime.fromtimestamp(created_at, UTC).replace(minute=0, second=0)
        if created_at_parse.hour not in [0, 11]:
            return abort(400, "Invalid timestamp, please give either UTC midnight or 11am (Trove time).")
        if created_at_parse.hour == 0:
            created_at_parse = created_at_parse.replace(hour=11)
        created_at = created_at_parse.timestamp()
    limit = int(params.get("limit", 0)) or None
    offset = int(params.get("offset", 0))
    query_dump = {}
    if query or created_at:
        query_dump = {
            "$and": [
                *([{"leaderboard_id": query}] if query else []),
                *([{"created_at": created_at}] if created_at else []),
            ]
        }
    final_query = LeaderboardEntry.find(query_dump).sort([("rank", 1)])
    entries = await final_query.skip(offset).limit(limit).to_list()
    entries_count = await final_query.count()
    response = render_json([i.model_dump() for i in entries])
    response.headers["count"] = entries_count
    return response

@leaderboards.route("/list", methods=["GET"])
async def get_list():
    items = await LeaderboardEntry.distinct("leaderboard_id")
    response = render_json(items)
    response.headers["count"] = len(items)
    return response

@leaderboards.route("/timestamps", methods=["GET"])
async def get_interest_items():
    timestamps = await LeaderboardEntry.distinct("created_at")
    return render_json(sorted(timestamps, reverse=True))

async def insert_leaderboard_data(raw_data):
    data = raw_data.get("data", "")
    leaderboard_regex = re.compile(r"^(.+?) = (.+?)##(.+$)$", re.MULTILINE)
    entry_regex = re.compile(r"^(\d{1,4});([^;]+?);([^;]+?)$", re.MULTILINE)
    leaderboards_imported = []
    submit_time = int(
        (datetime.now(UTC).replace(hour=11, minute=0, second=0, microsecond=0) - timedelta(days=1)).timestamp()
    )
    for leaderboard_id, name, raw_entries in leaderboard_regex.findall(data):
        leaderboards_imported.append(name)
        async with BulkWriter() as bw:
            for rank, player_name, score in entry_regex.findall("\n".join(raw_entries.split("|"))):
                await LeaderboardEntry.insert_one(
                    document=LeaderboardEntry(
                        leaderboard_id=leaderboard_id,
                        leaderboard_name=name,
                        player_name=player_name,
                        rank=int(rank),
                        score=float(score),
                        created_at=submit_time,
                    ),
                    bulk_writer=bw
                )
    async with ClientSession() as session:
        await session.get(f"https://trovesaurus.com/leaderboards?update&key={os.getenv('TROVESAURUS_MARKET_TOKEN')}")
    await send_embed(
        os.getenv("LEADERBOARD_WEBHOOK"),
        {
            "title": "Leaderboard Data inserted",
            "description": (
                f"{len(leaderboards_imported)} leaderboards were submitted."
            ),
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
