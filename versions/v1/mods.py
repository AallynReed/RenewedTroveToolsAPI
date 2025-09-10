import base64
import re
import traceback
from hashlib import md5
from io import BytesIO
from pathlib import Path

from aiohttp import ClientSession
from fuzzy_search import FuzzyPhraseSearcher
from quart import Blueprint, abort, current_app, request, send_file
from utils import render_json

from .models.database.mod import ModEntry, SearchMod, TMod, ZMod
from .utils.cache import SortOrder

mods_path = Path("mods")
mods_path.mkdir(parents=True, exist_ok=True)

mods = Blueprint("mods", __name__, url_prefix="/mods")


@mods.route("/")
async def index():
    return "Mods API"


@mods.route("/list", methods=["GET"])
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
    return render_json(
        current_app.mods_list.get_sorted_fields(*fields, limit=limit, offset=offset)
    )


@mods.route("/count", methods=["GET"])
async def get_mods_count():
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    return render_json({"count": len(current_app.mods_list)})


@mods.route("/tags", methods=["GET"])
async def get_tags():
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    return render_json(current_app.mods_list.get_mod_tags())


@mods.route("/subtags", methods=["GET"])
async def get_subtags():
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    return render_json(current_app.mods_list.get_mod_subtags())


@mods.route("/hash/<mod_hash>", methods=["GET"])
async def get_mod_by_hash(mod_hash):
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    return render_json(current_app.mods_list.get_mod_by_hash(mod_hash))


@mods.route("/hashes", methods=["GET"])
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
    return render_json(current_app.mods_list.get_all_hashed_mods(hashes))


@mods.route("/search", methods=["GET"])
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
    sort_by = params.get(
        "sort_by", "hot:desc,downloads:desc,likes:desc,name:asc,last_update:desc"
    )
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
                                {"name": {"$regex": ".*" + re.escape(query) + ".*"}},
                                {"authors": {"$in": [query]}},
                            ]
                        }
                    ]
                    if query is not None
                    else []
                ),
                *([{"type": type}] if type is not None else []),
                *([{"sub_type": sub_type}] if sub_type is not None else []),
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
    response = render_json(found)
    response.headers["count"] = mods_count
    return response


@mods.route("/types", methods=["GET"])
async def get_mod_types():
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    result = await SearchMod.distinct("type")
    return render_json([t for t in result if t])


@mods.route("/sub_types/<type>", methods=["GET"])
async def get_mod_sub_types(type):
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    if type in ["Costumes"]:
        result = await SearchMod.distinct("sub_type")
        return render_json([st for st in result if st])
    return render_json({})


@mods.route("preview_image/<hash>", methods=["GET"])
async def get_preview_image(hash):
    if not hasattr(current_app, "mods_list"):
        return abort(503, "Mods list is not populated.")
    cached_image_path = mods_path / f"cached_images/{hash}.png"
    if cached_image_path.exists():
        return await send_file(
            cached_image_path, attachment_filename=f"{hash}.png", as_attachment=True
        )
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
        return await send_file(
            BytesIO(), attachment_filename=f"{mod_entry.hash}.png", as_attachment=True
        )
    except Exception as e:
        print(e)
    return await send_file(
        "assets/no_preview.png",
        attachment_filename="no_preview.png",
        as_attachment=True,
    )

@mods.route("/downloadfile.php", methods=["GET"])
async def download_mod():
    params = request.args
    fileid = params.get("fileid", None)
    if fileid is None:
        return "No fileid provided", 400
    async with ClientSession() as session:
        async with session.get(f"https://trovesaurus.com/client/downloadfile.php?fileid={fileid}") as resp:
            if resp.status != 200:
                return f"Failed to download mod: {resp.status}", resp.status
            data = await resp.read()
            # Get file name from content-disposition header
            content_disposition = resp.headers.get("Content-Disposition", "")
            match = re.search(r'filename="(.+)"?', content_disposition)
            io = BytesIO(data)
            io.seek(0)
            try:
                mod = TMod.read_bytes(Path("temp.tmod"), data)
            except:
                try:
                    mod = ZMod.read_bytes(Path("temp.zmod"), data)
                except:
                    return "Failed to parse mod file", 500
            return await send_file(
                io,
                attachment_filename=f"{match.groups(1)[0]}",
                as_attachment=True,
                mimetype="application/octet-stream",
            )