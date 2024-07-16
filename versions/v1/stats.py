from quart import Blueprint, request, abort, current_app, send_file, Response
from PIL import Image
from enum import Enum
from aiohttp import ClientSession
from io import BytesIO
from pathlib import Path
from hashlib import md5
from versions.v1.models.database.api import API, Mastery
from versions.v1.utils.authorization import authorize
from json import loads
from base64 import b64encode
from utils import render_json
from versions.v1.utils.tooltip import Ally, Tooltip


stats = Blueprint("stats", __name__, url_prefix="/stats")
stats_folder = Path("versions/v1/data")
builds_file = stats_folder.joinpath("builds/builds.json")


@stats.route("/file/<path:u_path>", methods=["GET"])
async def file(u_path):
    file = stats_folder.joinpath(u_path)
    if file.exists():
        return await send_file(file)
    else:
        return abort(404)


@stats.route("/files", methods=["GET"])
async def files():
    return render_json(
        [
            str(x.relative_to(stats_folder))
            for x in stats_folder.rglob("*")
            if x.is_file()
        ]
    )


@stats.route("/get_data", methods=["GET"])
async def get_data():
    files = {}
    for x in stats_folder.rglob("*"):
        if x.is_file():
            file_name = str(x.relative_to(stats_folder).as_posix())
            files[file_name] = b64encode(x.read_bytes()).decode("utf-8")
    return render_json(files)


@stats.route("/mastery", methods=["GET"])
async def mastery():
    data = await API.find_one({"_id": "api"})
    if data is None:
        return abort(404)
    data = loads(data.json())["mastery"]
    return render_json(data)


@stats.route("/mastery", methods=["PUT"])
async def update_mastery():
    if not (user := await authorize(request)):
        return abort(401)
    if not user.is_admin:
        return abort(403)
    data = await request.json
    try:
        mastery_data = data["mastery_data"]
    except KeyError:
        return abort(400)
    mastery = await API.find_one({"_id": "api"})
    mastery.mastery = Mastery(
        normal=mastery_data["normal"],
        geode=mastery_data["geode"],
    )
    await mastery.save()
    return "OK", 200


@stats.route("/gear_builds", methods=["POST"])
async def gear_builds():
    builds = loads(builds_file.read_text())
    data = await request.form
    if not data.get("Token") == "YbiygMXSj2vtZc4YZhDy":
        return abort(403, "Invalid or missing token")
    c = data.get("class")
    t = data.get("type")
    if t == "dps":
        t = "light"
    build = builds[c][t]
    return render_json(build)


@stats.route("ally_tooltip/<name>")
async def ally_tooltip(name):
    data = loads(open("versions/v1/data/allies.json", "r").read())
    ally = data.get(name)
    if not ally:
        allies = []
        for x in data.values():
            if x["name"].lower() == name.replace("_", " ").lower():
                allies.append(Ally(x))
        for x in data.values():
            if x["name"].lower().startswith(name.replace("_", " ").lower()):
                allies.append(Ally(x))
        if not allies:
            return abort(404, "Ally not found")
        ally = allies[0]
    tooltip = Tooltip(ally)
    file = BytesIO()
    tooltip.generate_image().save(file, format="PNG")
    file.seek(0)
    return await send_file(
        file, mimetype="image/png", attachment_filename=f"{name}.png"
    )
