from quart import Blueprint, request, abort, jsonify, current_app, send_file
from .models.database.mod import ModEntry, ZMod
from .utils.cache import SortOrder
from pathlib import Path
from io import BytesIO

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
    return jsonify(current_app.mods_list.get_all_hashed_mods(hashes))

@mods.route('/search', methods=['GET'])
async def search_mods():
    ...


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