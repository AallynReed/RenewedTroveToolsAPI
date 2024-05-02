from .models.database.profile import ModProfile
from .models.database.mod import TMod, ZMod, TPack, ModEntry
from .utils.trovesaurus import ModAuthor
from quart import Blueprint, url_for, session, request, redirect, jsonify, abort, render_template, send_file, current_app
from datetime import datetime, UTC
from .utils.authorization import authorize
from hashlib import md5
from pathlib import Path
from base64 import b64decode
from io import BytesIO
from copy import deepcopy


mods_path = Path("mods")
mods_path.mkdir(parents=True, exist_ok=True)

profile_bp = Blueprint('profile', __name__, url_prefix='/profile', template_folder="templates")


@profile_bp.route('/')
async def index():
    return "Mod Profile API"


@profile_bp.route('/cloud_mods')
async def cloud_mods():
    data = dict(await request.json)
    try:
        mod_hashes = data["hashes"]
    except KeyError:
        return "Bad Request", 400
    mod_entries = await ModEntry.find_many({"hash": {"$in": mod_hashes}}).to_list()
    results = {}
    for hash in mod_hashes:
        results[hash] = None
        for entry in mod_entries:
            if entry.hash == hash:
                results[hash] = entry.dict()
                break
    return jsonify(results)


@profile_bp.route('/upload_cloud_mods', methods=['POST'])
async def upload_cloud_mods():
    data = dict(await request.json)
    try:
        mods = data["mods"]
    except KeyError:
        return "Bad Request", 400
    for mod_data in mods:
        entry = await ModEntry.find_one({"hash": mod_data["hash"]})
        if entry is not None:
            continue
        mod_bytes = b64decode(mod_data["data"])
        del mod_data["data"]
        entry = ModEntry(**mod_data)
        mod_path = mods_path.joinpath(f"{entry.hash}.{entry.format}")
        mod_path.write_bytes(mod_bytes)
        await entry.save()
    return "OK", 200


@profile_bp.route('/create', methods=['POST'])
async def create_profile():
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profiles = await ModProfile.find_many({"owner_id": user.discord_id, "deleted": False}).to_list()
    if len(profiles) >= user.mod_profiles_limit:
        return "Profile Limit Exceeded", 400
    data = dict(await request.json)
    profile = ModProfile(
        name=data["name"],
        description=data["description"],
        image_url=data.get("image_url", None),
        mod_hashes=data.get("mod_hashes", []),
        owner_id=user.discord_id
    )
    await profile.save()
    return "OK", 200


@profile_bp.route('/list_profiles', methods=['GET'])
async def list_profiles():
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profiles = await ModProfile.find_many({"owner_id": user.discord_id, "deleted": False}, fetch_links=True).to_list()
    for profile in profiles:
        hashes = [mod.hash for mod in profile.mods]
        trovesaurus_mods = {}
        for hash, data in current_app.mods_list.get_all_hashed_mods(hashes).items():
            if data is None:
                continue
            trovesaurus_mods[hash] = ModEntry(
                hash=hash,
                mod_id=data["id"],
                name=data["name"],
                format=[
                    f
                    for f in data["downloads"]
                    if f["hash"] == hash
                ][0]["format"],
                authors=[ModAuthor(**a) for a in data["authors"]],
                description=data["description"],
            )
        profile.mods = [
            trovesaurus_mods.get(mod.hash, mod)
            for mod in profile.mods
        ]
    result = [profile.dict() for profile in profiles]
    for profile in result:
        profile["clones"] = await ModProfile.find({"clone_of": profile["profile_id"]}).count()
    return jsonify(result)


@profile_bp.route('/get/<profile_id>', methods=['GET'])
async def get_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "$or": [{"owner_id": user.discord_id}, {"shared": True}]},
        fetch_links=True
    )
    if profile is None:
        return "Not Found", 404
    return jsonify(profile.dict())


@profile_bp.route('/update/<profile_id>', methods=['PUT'])
async def update_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    data = await request.json
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "owner_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    profile.name = data.get("name", profile.name)
    profile.description = data.get("description", profile.description)
    profile.image_url = data.get("image_url", profile.image_url)
    await profile.save()
    return "OK", 200


@profile_bp.route('/delete/<profile_id>', methods=['DELETE'])
async def delete_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "owner_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    profile.deleted = True
    await profile.save()
    return "OK", 200


@profile_bp.route('/like/<profile_id>', methods=['POST'])
async def like_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "$or": [{"owner_id": user.discord_id}, {"shared": True}]}
    )
    if profile is None:
        return "Not Found", 404
    if user.discord_id in profile.likes:
        return "Already Liked", 400
    profile.likes.append(user.discord_id)
    await profile.save()
    return "OK", 200


@profile_bp.route('/unlike/<profile_id>', methods=['POST'])
async def unlike_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "$or": [{"owner_id": user.discord_id}, {"shared": True}]}
    )
    if profile is None:
        return "Not Found", 404
    if user.discord_id not in profile.likes:
        return "Not Liked", 400
    profile.likes.remove(user.discord_id)
    await profile.save()
    return "OK", 200


@profile_bp.route('/clone/<profile_id>', methods=['POST'])
async def clone_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "$or": [{"owner_id": user.discord_id}, {"shared": True}], "deleted": False}, fetch_links=True
    )
    if profile is None:
        return "Not Found", 404
    if profile.shared is False:
        return "Not Shared", 401
    if profile.clone_of is not None:
        return "Already Cloned", 400
    mods = []
    for mod in profile.mods:
        if mod in profile.private_mods:
            continue
        mods.append(mod)
    clone = ModProfile(
        name=profile.name,
        description=profile.description,
        image_url=profile.image_url,
        mods=mods,
        private_mods=[],
        discord_id=user.discord_id,
        shared=False,
        likes=[],
        deleted=False,
        clone_of=profile.profile_id
    )
    await clone.save()
    return jsonify(clone.dict())


@profile_bp.route('/share/<profile_id>', methods=['POST'])
async def share_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "owner_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    profile.shared = True
    await profile.save()
    return "OK", 200


@profile_bp.route('/unshare/<profile_id>', methods=['POST'])
async def unshare_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "owner_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    profile.shared = False
    await profile.save()
    return "OK", 200


@profile_bp.route('/sync/<profile_id>', methods=['POST'])
async def sync_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "owner_id": user.discord_id, "$ne": {"clone_of": None}}
    )
    if profile is None:
        return "Not Found", 404
    profile.sync = True
    await profile.save()
    return "OK", 200


@profile_bp.route('/unsync/<profile_id>', methods=['POST'])
async def unsync_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "owner_id": user.discord_id, "$ne": {"clone_of": None}}
    )
    if profile is None:
        return "Not Found", 404
    profile.sync = False
    await profile.save()
    return "OK", 200


@profile_bp.route('/mod_hashes/<profile_id>', methods=['POST'])
async def add_mod_hashes(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "owner_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    data = await request.json
    for mod_hash in data["hashes"]:
        mod_entry = await ModEntry.find_one({"hash": mod_hash})
        if not mod_entry:
            return "An error occurred while adding mods", 500
        profile.mods.append(mod_entry)
    await profile.save()
    return "OK", 200


@profile_bp.route('/mod_hashes/<profile_id>', methods=['DELETE'])
async def remove_mod_hashes(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "owner_id": user.discord_id},
        fetch_links=True
    )
    if profile is None:
        return "Not Found", 404
    data = await request.json
    for mod in deepcopy(profile.mods):
        if mod.hash in data["hashes"]:
            profile.mods.remove(mod)
    await profile.save()
    return "OK", 200


@profile_bp.route('/download/<profile_id>', methods=['GET'])
async def download_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "$or": [{"owner_id": user.discord_id}, {"shared": True}]}
    )
    if profile is None:
        return "Not Found", 404
    mods = []
    for hash in profile.mod_hashes:
        mod_info = await ModEntry.find_one({"hash": hash})
        mod_path = Path(f"mods/{hash}.{mod_info.format}")
        if not mod_path.exists():
            return "One of the mods wasn't found, please report this to \"sly.dev.\" on discord", 503
        if mod_info.format == "zip":
            mod = ZMod.read_bytes(mod_path, BytesIO(mod_path.read_bytes()))
            mod.name = mod_info.name
        else:
            mod = TMod.read_bytes(mod_path, mod_path.read_bytes())
        mods.append(mod)
    pack = TPack()
    pack.author = "sly.dev."
    pack.files.extend(mods)
    data = pack.compile()
    return await send_file(BytesIO(data), as_attachment=True, attachment_filename=f"{profile_id}.tpack")
