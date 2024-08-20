from quart import Blueprint, request, abort
from .models.database.scraping import ChaosChestEntry, ChallengeEntry
from utils import render_json
import os
from aiohttp import ClientSession
from .utils.discord import send_embed
from datetime import datetime, UTC


rotations = Blueprint("rotations", __name__, url_prefix="/rotations")


@rotations.route("/chaoschest", methods=["GET"])
async def get_chaoschest():
    data = await ChaosChestEntry.find().sort(("created_at", -1)).limit(1).to_list()
    return render_json(data[0].model_dump(exclude=["id"]))


@rotations.route("/chaoschest/history", methods=["GET"])
async def get_chaoschest_history():
    data = await ChaosChestEntry.find().sort(("created_at", -1)).to_list()
    return render_json([entry.model_dump(exclude=["id"]) for entry in data])


@rotations.route("/chaoschest/insert", methods=["POST"])
async def insert_chaoschest():
    raw_data = await request.form
    if raw_data.get("Token") != os.getenv("TOKEN"):
        return abort(401)
    now = (
        datetime.now(UTC)
        .replace(hour=11, minute=0, second=0, microsecond=0)
        .timestamp()
    )
    item = raw_data.get("item")
    await ChaosChestEntry(item=item, created_at=now).save()
    async with ClientSession() as session:
        await session.get(
            f"https://trovesaurus.com/chaoschests?token={os.getenv('TROVESAURUS_ROTATIONS_TOKEN')}&name={item}"
        )
    await send_embed(
        os.getenv("CHAOSCHEST_WEBHOOK"),
        {
            "title": "Chaos Chest Data inserted",
            "description": (f"**{item}** was set as Chaos Chest item."),
            "color": 0x00FF00,
        },
    )
    return "OK", 200


@rotations.route("/challenge", methods=["GET"])
async def get_challenge():
    data = await ChallengeEntry.find().sort(("created_at", -1)).limit(1).to_list()
    return render_json(data[0].model_dump(exclude=["id"]))


@rotations.route("/challenge/history", methods=["GET"])
async def get_challenge_history():
    data = await ChallengeEntry.find().sort(("created_at", -1)).to_list()
    return render_json([entry.model_dump(exclude=["id"]) for entry in data])


@rotations.route("/challenge/insert", methods=["POST"])
async def insert_challenge():
    raw_data = await request.form
    if raw_data.get("Token") != os.getenv("TOKEN"):
        return abort(401)
    now = datetime.now(UTC)
    if now.minute < 30:
        now = now.replace(minute=0, second=0, microsecond=0).timestamp()
    else:
        now = now.replace(minute=30, second=0, microsecond=0).timestamp()
    challenge = raw_data.get("challenge")
    await ChallengeEntry(name=challenge, created_at=now).save()
    async with ClientSession() as session:
        await session.get(
            f"https://trovesaurus.com/challenges?token={os.getenv('TROVESAURUS_ROTATIONS_TOKEN')}&name={challenge}&timestamp={now}"
        )
    await send_embed(
        os.getenv("CHALLENGE_WEBHOOK"),
        {
            "title": "Hourly Challenge Data inserted",
            "description": (f"**{challenge}** was set as Hourly Challenge."),
            "color": 0x00FF00,
        },
    )
    return "OK", 200
