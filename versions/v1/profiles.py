from .models.database.profile import ModProfile
from .models.database.mod import TMod, ZMod, TPack, ModEntry
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
    profiles = await ModProfile.find_many({"discord_id": user.discord_id, "deleted": False}).to_list()
    if len(profiles) >= user.mod_profiles_limit:
        return "Profile Limit Exceeded", 400
    data = dict(await request.json)
    profile = ModProfile(
        name=data["name"],
        description=data["description"],
        image_url=data.get("image_url", None),
        mod_hashes=data.get("mod_hashes", []),
        discord_id=user.discord_id
    )
    await profile.save()
    return "OK", 200


@profile_bp.route('/list_profiles', methods=['GET'])
async def list_profiles():
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profiles = await ModProfile.find_many({"discord_id": user.discord_id, "deleted": False}).to_list()
    return jsonify([profile.dict() for profile in profiles])


@profile_bp.route('/get/<profile_id>', methods=['GET'])
async def get_profile(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "$or": [{"discord_id": user.discord_id}, {"shared": True}]},
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
        {"profile_id": profile_id, "discord_id": user.discord_id}
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
        {"profile_id": profile_id, "discord_id": user.discord_id}
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
        {"profile_id": profile_id, "$or": [{"discord_id": user.discord_id}, {"shared": True}]}
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
        {"profile_id": profile_id, "$or": [{"discord_id": user.discord_id}, {"shared": True}]}
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
        {"profile_id": profile_id, "$or": [{"discord_id": user.discord_id}, {"shared": True}]}
    )
    if profile is None:
        return "Not Found", 404
    if profile.shared is False:
        return "Not Shared", 401
    clone = ModProfile(
        name=profile.name,
        description=profile.description,
        image_url=profile.image_url,
        mods=profile.mods,
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
        {"profile_id": profile_id, "discord_id": user.discord_id}
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
        {"profile_id": profile_id, "discord_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    profile.shared = False
    await profile.save()
    return "OK", 200


@profile_bp.route('/mod_hashes/<profile_id>', methods=['POST'])
async def add_mod_hashes(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "discord_id": user.discord_id}
    )
    if profile is None:
        return "Not Found", 404
    data = await request.json
    for mod_hash, mod_data in data["mod_hashes"].items():
        mod_entry = await ModEntry.find_one({"hash": mod_hash})
        if mod_entry is None:
            mod_entry = ModEntry(
                hash=mod_hash,
                name=mod_data["name"],
                format=mod_data["format"],
                author=mod_data["author"],
                description=mod_data["description"],
                image_url=mod_data.get("image_url", None)
            )
            mod_path = Path(f"mods/{mod_hash}.{mod_data["format"]}")
            if not mod_path.exists():
                with open(mod_path, "wb") as f:
                    f.write(b64decode(mod_data["data"]))
            await mod_entry.save()
        if mod_entry not in profile.mods:
            profile.mods.append(mod_entry)
    await profile.save()
    return "OK", 200


@profile_bp.route('/mod_hashes/<profile_id>', methods=['DELETE'])
async def remove_mod_hashes(profile_id):
    if (user := await authorize(request)) is None:
        return "Unauthorized", 401
    profile = await ModProfile.find_one(
        {"profile_id": profile_id, "discord_id": user.discord_id},
        fetch_links=True
    )
    if profile is None:
        return "Not Found", 404
    data = await request.json
    for mod_hash in data["mod_hashes"]:
        mod_entry = await ModEntry.find_one({"hash": mod_hash})
        if not mod_entry:
            continue
        if mod_entry in profile.mods:
            profile.mods.remove(mod_entry)
    await profile.save()
    return "OK", 200


@profile_bp.route('/download/<profile_id>', methods=['GET'])
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
