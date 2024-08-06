from quart import Blueprint, request, abort, current_app, send_file, Response
from .models.database.scraping import ChaosChestEntry, ChallengeEntry, ChallengeType
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
    now = datetime.now(UTC).replace(hour=11, minute=0, second=0, microsecond=0).timestamp()
    item = raw_data.get("item")
    await ChaosChestEntry(
        item=item,
        created_at=now
    ).save()
    async with ClientSession() as session:
        await session.get(
            f"https://trovesaurus.com/chaoschests?token={os.getenv('TROVESAURUS_ROTATIONS_TOKEN')}&name={item}"
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
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0).timestamp()
    challenge = raw_data.get("challenge")
    await ChallengeEntry(
        name=challenge,
        created_at=now
    ).save()
    async with ClientSession() as session:
        await session.get(
            f"https://trovesaurus.com/challenges?token={os.getenv('TROVESAURUS_ROTATIONS_TOKEN')}&name={challenge}"
        )
    return "OK", 200