from quart import Blueprint, request, abort, jsonify, json
from .models.database.star import StarBuild


star = Blueprint('star', __name__, url_prefix='/star_chart')


@star.route('/build_paths', methods=['GET'])
async def get_build_by_paths():
    _fields = [
        ["paths", list]
    ]
    form = json.loads((await request.data).decode("utf-8"))
    missing = []
    invalid = []
    for field in _fields:
        if field[0] not in form:
            missing.append(field[0])
        elif not isinstance(form[field[0]], field[1]):
            invalid.append(field[0])
    if missing or invalid:
        return await abort(
            400,
            {
                "message": "Missing or invalid fields.",
                "missing": missing,
                "invalid": invalid
            }
        )
    build = await StarBuild.find_one({"paths": {"$all": [], "$size": 0}})
    if not build:
        build = StarBuild(paths=form["paths"])
        await build.save()
    return jsonify(build.model_dump_json())
