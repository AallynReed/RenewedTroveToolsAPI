from quart import (
    Blueprint,
    url_for,
    request,
    abort,
    send_file,
)
from pathlib import Path
from random import choices
from string import ascii_letters, digits
import os


def generate_random_string(length: int) -> str:
    return "".join(choices(ascii_letters + digits, k=length))


personal_path = Path("personal")
personal_path.mkdir(parents=True, exist_ok=True)
upload_path = personal_path / "upload"
upload_path.mkdir(parents=True, exist_ok=True)
images_path = upload_path / "images"
images_path.mkdir(parents=True, exist_ok=True)

personal_bp = Blueprint(
    "personal", __name__, url_prefix="/p", template_folder="templates", subdomain="cdn"
)


@personal_bp.route("/upload", methods=["POST"])
async def upload_image():
    token = request.headers.get("Token")
    if token != os.getenv("UPLOAD_TOKEN"):
        return abort(401)
    files = await request.files
    if "image" not in files:
        return abort(400)
    image = files["image"]
    name = generate_random_string(7)
    extension = image.filename.split(".")[-1]
    file_name = f"{name}.{extension}"
    await image.save(images_path / file_name)
    return "https://cdn.aallyn.xyz" + url_for("personal.get_image", filename=file_name)


@personal_bp.route("/<filename>")
async def get_image(filename):
    return await send_file(images_path / filename)
