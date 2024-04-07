from quart import Blueprint, request, abort, jsonify, current_app, send_file, Response
from .models.database.mod import ModEntry, ZMod, TMod, SearchMod
from .utils.cache import SortOrder
from pathlib import Path
from io import BytesIO
import base64
import traceback
import urllib.parse
import re

mods_path = Path("mods")
mods_path.mkdir(parents=True, exist_ok=True)

mods = Blueprint('mods', __name__, url_prefix='/mods')

@mods.route('/')
async def index():
    return "Mods API"

@mods.route('/list', methods=['GET'])
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


@mods.route('/count', methods=['GET'])
async def get_mods_count():
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    return jsonify({"count": len(current_app.mods_list)})


@mods.route('/tags', methods=['GET'])
async def get_tags():
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    return jsonify(current_app.mods_list.get_mod_tags())

@mods.route('/subtags', methods=['GET'])
async def get_subtags():
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    return jsonify(current_app.mods_list.get_mod_subtags())

@mods.route('/hash/<mod_hash>', methods=['GET'])
async def get_mod_by_hash(mod_hash):
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    return jsonify(current_app.mods_list.get_mod_by_hash(mod_hash))

@mods.route('/hashes', methods=['GET'])
async def get_mods_by_hashes():
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    params = request.args
    hashes = params.get("hashes", "").split("#")
    hashes = [h for h in hashes if h]
    if not hashes:
        data = await request.json
        if data is None:
            return "No hashes provided", 400
        hashes = data.get("hashes")
    return jsonify(current_app.mods_list.get_all_hashed_mods(hashes))

@mods.route('/search', methods=['GET'])
async def search_mods():
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    mods_list = current_app.mods_list
    params = request.args
    query = params.get("query", None)
    if query is not None:
        query = query.lower()
    type = params.get("type", None)
    sub_type = params.get("sub_type", None)
    limit = int(params.get("limit", 999999))
    offset = int(params.get("offset", 0))
    sort_by = params.get("sort_by", "downloads:desc,likes:desc,name:asc,last_update:desc")
    processed_sort_by = [
        (field, SortOrder[order].value)
        for field, order in (field.split(":") for field in sort_by.split(","))
    ]
    if query is None and type is None and sub_type is None:
        query_dump = {}
    else:
        query_dump = {
            "$and": [
                *(
                    [
                        {
                            "$or": [
                                {"name": {"$regex": ".*" + query + ".*"}},
                                {"authors": {"$in": [query]}},
                            ]
                        }
                    ] if query is not None else []
                ),
                *(
                    [
                        {"type": type}
                    ] if type is not None else []
                ),
                *(
                    [
                        {"sub_type": sub_type}
                    ] if sub_type is not None else []
                )
            ]
        }
    try:
        final_query = SearchMod.find(query_dump).sort(processed_sort_by)
        if query is not None and re.match(r"^\d*$", query):
            final_query = SearchMod.find({"_id": int(query)})
        mods = await final_query.skip(offset).limit(limit).to_list()
        mods_count = await final_query.count()
    except:
        traceback.print_exc()
        return "Failed to search mods", 200
    found = []
    for mod in mods:
        found_mod = mods_list[str(mod.id)]
        if found_mod is None:
            await mod.delete()
            continue
        found.append(found_mod.model_dump(by_alias=True))
    response = jsonify(found)
    response.headers["count"] = mods_count
    return response

@mods.route('/types', methods=['GET'])
async def get_mod_types():
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    result = await SearchMod.distinct("type")
    return jsonify([t for t in result if t])

@mods.route('/sub_types/<type>', methods=['GET'])
async def get_mod_sub_types(type):
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    if type in ["Costumes"]:
        result = await SearchMod.distinct("sub_type")
        return jsonify([st for st in result if st])
    return jsonify({})

@mods.route('/tmod_converter/<hash>', methods=['GET'])
async def convert_tmod(hash):
    return "Not Implemented", 501
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    mod_entry = await ModEntry.find_one({"hash": hash})
    if mod_entry is None:
        return "Mod not found", 404
    if mod_entry.format == "tmod":
        return "Mod is already in tmod format", 400
    mod_path = mods_path / f"{hash}.{mod_entry.format}"
    if not mod_path.exists():
        return "Mod file not found", 404
    mod = ZMod.read_bytes(mod_path, BytesIO(mod_path.read_bytes()))
    mod.author = mod_entry.author
    mod.name = mod_entry.name
    mod.notes = mod_entry.description
    return await send_file(BytesIO(mod.tmod_content), attachment_filename=f"{mod_entry.name}.tmod", as_attachment=True)

@mods.route('preview_image/<hash>', methods=['GET'])
async def get_preview_image(hash):
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    cached_image_path = mods_path / f"cached_images/{hash}.png"
    if cached_image_path.exists():
        return await send_file(cached_image_path, attachment_filename=f"{hash}.png", as_attachment=True)
    mod_entry = await ModEntry.find_one({"hash": hash})
    if mod_entry is None:
        return "Mod not found", 404
    mod_path = mods_path / f"{hash}.{mod_entry.format}"
    if not mod_path.exists():
        return "Mod file not found", 404
    try:
        mod = TMod.read_bytes(mod_path, mod_path.read_bytes())
        image_data = base64.b64decode(mod.image)
        image_path = mods_path / f"cached_images/{hash}.png"
        image_path.write_bytes(image_data)
        return await send_file(BytesIO(), attachment_filename=f"{mod_entry.hash}.png", as_attachment=True)
    except Exception as e:
        print(e)
    return await send_file("assets/construction.png", attachment_filename="construction.png", as_attachment=True)
    