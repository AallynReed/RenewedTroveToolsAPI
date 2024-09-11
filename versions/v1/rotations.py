from quart import Blueprint, request, abort, current_app
from .models.database.scraping import ChaosChestEntry, ChallengeEntry
from utils import render_json, Event, EventType
import os
from aiohttp import ClientSession
from .utils.discord import send_embed
from datetime import datetime, UTC
import re


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
    chaos_chest = await ChaosChestEntry(item=item, created_at=now).save()
    async with ClientSession() as session:
        await session.get(
            f"https://trovesaurus.com/chaoschests?token={os.getenv('TROVESAURUS_ROTATIONS_TOKEN')}&name={item}"
        )
    await current_app.redis.publish_event(
        Event(
            id=int(now),
            type=EventType.chaoschest,
            data=chaos_chest.model_dump(exclude=["id"]),
        )
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
    challenge_entry = await ChallengeEntry(name=challenge, created_at=now).save()
    async with ClientSession() as session:
        await session.get(
            f"https://trovesaurus.com/challenges?token={os.getenv('TROVESAURUS_ROTATIONS_TOKEN')}&name={challenge}&timestamp={now}"
        )
    await current_app.redis.publish_event(
        Event(
            id=int(now),
            type=EventType.challenge,
            data=challenge_entry.model_dump(exclude=["id"]),
        )
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


@rotations.route("/challenge/insert_missing", methods=["GET", "POST"])
async def insert_missing_challenge():
    if request.method == "GET":
        return """
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="files[]" multiple>
            <input type="submit">
        </form>
        """
    files = await request.files
    if "files[]" not in files:
        return abort(400)
    response = []
    for file in files.getlist("files[]"):
        timestamp = int(file.filename.split(".")[0])
        time = datetime.fromtimestamp(timestamp, UTC)
        if time.minute < 30:
            time = time.replace(minute=0, second=0, microsecond=0).timestamp()
        else:
            time = time.replace(minute=30, second=0, microsecond=0).timestamp()
        challenge = re.findall(
            r"^challenge = (.*+)$", file.read().decode("utf-8"), re.MULTILINE
        )
        if not challenge:
            return abort(400)
        challenge_entry = await ChallengeEntry.find_one({"created_at": int(time)})
        if challenge_entry:
            challenge_entry.name = challenge[0]
            await challenge_entry.save()
        else:
            challenge_entry = await ChallengeEntry(
                name=challenge[0], created_at=int(time)
            ).save()
        async with ClientSession() as session:
            url = f"https://trovesaurus.com/challenges?token={os.getenv('TROVESAURUS_ROTATIONS_TOKEN')}&name={challenge[0]}&timestamp={time}"
            resp = await session.get(url)
            response.append(await resp.text())
        await current_app.redis.publish_event(
            Event(
                id=int(time),
                type=EventType.challenge,
                data=challenge_entry.model_dump(exclude=["id"]),
            )
        )
    return "\n".join(response), 200


@rotations.route("/luxion", methods=["GET"])
async def luxion():
    luxion_rotations = current_app.trove_time.get_luxion_rotations()
    return render_json(luxion_rotations)


@rotations.route("/corruxion", methods=["GET"])
async def corruxion():
    corruxion_rotations = current_app.trove_time.get_corruxion_rotations()
    return render_json(corruxion_rotations)


@rotations.route("/fluxion", methods=["GET"])
async def fluxion():
    fluxion_rotations = current_app.trove_time.get_fluxion_rotations()
    return render_json(fluxion_rotations)
