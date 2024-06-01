from quart import Blueprint, request, abort, json
from .models.database.gem import GemBuild, BuildConfig
from pydantic import ValidationError
from utils import render_json


gem = Blueprint("gem", __name__, url_prefix="/gem_builds")


@gem.route("/")
async def index():
    return "Gem Builds API"


@gem.route("/build/<build>", methods=["GET"])
async def get_build_by_id(build):
    build = await GemBuild.find_one({"build": build})
    if not build:
        return abort(404, "Build not found.")
    return render_json(build.model_dump_json())


@gem.route("/build_config", methods=["GET"])
async def get_build_by_config():
    headers = request.headers
    config = json.loads(headers.get("config"))
    try:
        build_config = BuildConfig(**config)
    except ValidationError:
        return abort(400, "Invalid Build Config")
    build = await GemBuild.find_one({"config": build_config.dict()})
    if not build:
        build = GemBuild(config=build_config)
        await build.save()
    return render_json(build.model_dump_json())
