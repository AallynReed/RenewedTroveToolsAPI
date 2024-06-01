from quart import Blueprint, request, abort, json
from .models.database.star import StarBuild
from utils import render_json


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
