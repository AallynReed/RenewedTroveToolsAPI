from quart import Blueprint, request, abort, json
from .models.database.star import StarBuild
from utils import render_json
from versions.v1.utils.authorization import authorize


star = Blueprint("star", __name__, url_prefix="/star_chart")


@star.route("/")
async def index():
    return "Star Chart API"


@star.route("/build/<build>", methods=["GET"])
async def get_build_by_id(build):
    build = await StarBuild.find_one({"build": build})
    if not build:
        return abort(404, "Build not found.")
    return render_json(build.model_dump_json())


@star.route("/build_paths", methods=["GET"])
async def get_build_by_paths():
    params = request.args
    paths = params.get("paths", "").split("$")
    build = await StarBuild.find_one({"paths": {"$all": paths, "$size": len(paths)}})
    if not build:
        build = StarBuild(paths=paths)
        await build.save()
    return render_json(build.model_dump_json())


@star.route("/presets", methods=["GET"])
async def get_presets():
    presets = await StarBuild.find({"preset.toggle": True}).to_list(length=9999)
    presets = [preset.model_dump() for preset in presets]
    return render_json(presets)


@star.route("/preset/<build>", methods=["GET"])
async def get_preset(build):
    preset = await StarBuild.find_one({"build": build, "preset.toggle": True})
    if not preset:
        return abort(404, "Preset not found.")
    return render_json(preset.model_dump())


@star.route("/preset/<build>", methods=["DELETE"])
async def delete_preset(build):
    if not (user := await authorize(request)):
        return abort(401)
    if not user.is_admin:
        return abort(403)
    preset = await StarBuild.find_one({"build": build, "preset.toggle": True})
    if not preset:
        return abort(404, "Preset not found.")
    preset.preset.toggle = False
    await preset.save()
    return "OK", 200


@star.route("/preset/<build>", methods=["PUT"])
async def update_preset(build):
    if not (user := await authorize(request)):
        return abort(401)
    if not user.is_admin:
        return abort(403)
    preset = await StarBuild.find_one({"build": build, "preset.toggle": True})
    if not preset:
        return abort(404, "Preset not found.")
    data = await request.json
    preset.preset.name = data.get("name", preset.preset.name)
    preset.preset.toggle = data.get("toggle", preset.preset.toggle)
    await preset.save()
    return "OK", 200
