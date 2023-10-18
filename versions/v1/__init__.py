from quart import Blueprint, request, jsonify, current_app, abort
from .star_chart import star
# from .mods import mods
from .utils.cache import SortOrder


api_v1 = Blueprint('api_v1', __name__, url_prefix='/v1', subdomain="kiwiapi")
# Register Endpoints
api_v1.register_blueprint(star)
# api_v1.register_blueprint(mods)


@api_v1.route('/mods/list', methods=['GET'])
async def get_mods():
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    params = request.args
    raw_fields = params.get("sort", "").split("#")
    fields = []
    for field in raw_fields:
        if not field:
            continue
        key, value = field.split("$")
        fields.append((key, SortOrder(value)))
    limit = int(params.get("limit", 0)) or None
    offset = int(params.get("offset", 0)) or None
    return jsonify(current_app.mods_list.get_sorted_fields(*fields, limit=limit, offset=offset))


@api_v1.route('/mods/search', methods=['GET'])
async def search_mods():
    ...
