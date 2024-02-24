from .models.database.profile import ModProfile
from .models.database.trovesaurus import ModEntry
from .models.database.mod import TMod, ZMod, TPack
from quart import Blueprint, url_for, session, request, redirect, jsonify, abort, render_template, send_file
from datetime import datetime, UTC
from .utils.authorization import authorize
from hashlib import md5
from pathlib import Path
from base64 import b64decode
from io import BytesIO


profile_bp = Blueprint('profile', __name__, url_prefix='/profile', template_folder="templates")


@profile_bp.route('/')
async def index():
    return "Mod Profile API"

@profile_bp.route('/create', methods=['POST'])
async def create_profile():
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    data = await request.json
    profile = ModProfile(
        name=data["name"],
        description=data["description"],
        image_url=data.get("image_url", None),
        discord_id=user.discord_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    await profile.save()
    return "OK", 200

@profile_bp.route('/<profile_id>', methods=['GET'])
async def get_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "$or": [{"discord_id": user.discord_id}, {"shared": True}]}
    )
    if profile is None:
        return "Not Found", 404
    return jsonify(profile.dict())

@profile_bp.route('/<profile_id>', methods=['PUT'])
async def update_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    data = await request.json
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "discord_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    profile.name = data.get("name", profile.name)
    profile.description = data.get("description", profile.description)
    profile.image_url = data.get("image_url", profile.image_url)
    profile.updated_at = datetime.now(UTC)
    await profile.save()
    return "OK", 200

@profile_bp.route('/<profile_id>', methods=['DELETE'])
async def delete_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "discord_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    profile.deleted = True
    profile.updated_at = datetime.now(UTC)
    await profile.save()
    return "OK", 200

@profile_bp.route('/<profile_id>/like', methods=['POST'])
async def like_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "$or": [{"discord_id": user.discord_id}, {"shared": True}]}
    )
    if profile is None:
        return "Not Found", 404
    if user.discord_id in profile.likes:
        return "Already Liked", 400
    profile.likes.append(user.discord_id)
    await profile.save()
    return "OK", 200

@profile_bp.route('/<profile_id>/unlike', methods=['POST'])
async def unlike_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "$or": [{"discord_id": user.discord_id}, {"shared": True}]}
    )
    if profile is None:
        return "Not Found", 404
    if user.discord_id not in profile.likes:
        return "Not Liked", 400
    profile.likes.remove(user.discord_id)
    await profile.save()
    return "OK", 200

@profile_bp.route('/<profile_id>/clone', methods=['POST'])
async def clone_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "$or": [{"discord_id": user.discord_id}, {"shared": True}]}
    )
    if profile is None:
        return "Not Found", 404
    if profile.shared is False:
        return "Not Shared", 400
    clone = profile.model_copy()
    clone.discord_id = user.discord_id
    clone.shared = False
    clone.likes = []
    clone.clone_of = profile.profile_id
    await clone.save()
    return jsonify(clone.dict())


@profile_bp.route('/<profile_id>/share', methods=['POST'])
async def share_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "discord_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    profile.shared = True
    profile.updated_at = datetime.now(UTC)
    await profile.save()
    return "OK", 200


@profile_bp.route('/<profile_id>/unshare', methods=['POST'])
async def unshare_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "discord_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    profile.shared = False
    profile.updated_at = datetime.now(UTC)
    await profile.save()
    return "OK", 200

@profile_bp.route('/<profile_id>/mod_hashes', methods=['POST'])
async def add_mod_hashes(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "discord_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    data = await request.json
    profile.mod_hashes.extend(list(data["mod_hashes"].keys()))
    for mod_hash, mod_data in data["mod_hashes"].items():
        mod_path = Path(f"mods/{mod_hash}.{mod_data["format"]}")
        if not mod_path.exists():
            with open(mod_path, "wb") as f:
                f.write(b64decode(mod_data["data"]))
    profile.updated_at = datetime.now(UTC)
    await profile.save()
    return "OK", 200


@profile_bp.route('/<profile_id>/mod_hashes', methods=['DELETE'])
async def remove_mod_hashes(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "discord_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    data = await request.json
    for mod_hash in data["mod_hashes"]:
        if mod_hash in profile.mod_hashes:
            profile.mod_hashes.remove(mod_hash)
    profile.updated_at = datetime.now(UTC)
    await profile.save()
    return "OK", 200


@profile_bp.route('/<profile_id>/mod_hashes', methods=['PUT'])
async def set_mod_hashes(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "discord_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    data = await request.json
    profile.mod_hashes = list(data["mod_hashes"].keys())
    for mod_hash, mod_data in data["mod_hashes"].items():
        mod_path = Path(f"mods/{mod_hash}.{mod_data["format"]}")
        if not mod_path.exists():
            with open(mod_path, "wb") as f:
                f.write(b64decode(mod_data["data"]))
    await profile.save()
    return "OK", 200


@profile_bp.route('/<profile_id>/download', methods=['GET'])
async def download_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "$or": [{"discord_id": user.discord_id}, {"shared": True}]}
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
