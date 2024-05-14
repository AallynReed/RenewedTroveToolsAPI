from quart import Blueprint, request, abort, jsonify, current_app, send_file, Response
from PIL import Image
from enum import Enum
from aiohttp import ClientSession
from io import BytesIO
from pathlib import Path
from hashlib import md5

images_cache = Path("image_cache")
images_cache.mkdir(parents=True, exist_ok=True)

image = Blueprint("image", __name__, url_prefix="/image")


class ImageSize(Enum):
    MINI = 24
    TINY = 32
    SMALL = 64
    MEDIUM = 128
    LARGE = 256
    HUGE = 512
    MAX = 1024


@image.route("/resize", methods=["GET"])
async def resize_image():
    params = request.args
    url = params.get("url")
    if not url:
        return abort(400, "Missing URL")
    try:
        size = ImageSize[params.get("size", "MEDIUM")]
    except ValueError:
        return abort(
            400,
            "Invalid size\nValid sizes: MINI, TINY, SMALL, MEDIUM, LARGE, HUGE, MAX",
        )
    url = url.replace("//imgur.", "//i.imgur.")
    if "imgur" in url and not any(
        url.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]
    ):
        url += ".png"
    hash_string = url + size.name
    hash = md5(hash_string.encode()).hexdigest()
    cached_image = images_cache / (hash + ".png")
    if cached_image.exists():
        return await send_file(cached_image, mimetype="image/png")
    async with ClientSession() as session:
        async with session.get(url, allow_redirects=True) as response:
            if response.status == 429:
                return abort(400, "Ratelimit reached")
            if response.status != 200:
                return abort(400, "Invalid URL")
            image_bytes = await response.read()
            image = Image.open(BytesIO(image_bytes))
            image_w, image_h = image.size
            if image_w < size.value or image_h < size.value:
                cached_image.write_bytes(image_bytes)
                return await send_file(BytesIO(image_bytes), mimetype="image/png")
            ratio = size.value / max(image_w, image_h)
            new_w = int(image_w * ratio)
            new_h = int(image_h * ratio)
            image = image.resize((new_w, new_h))
            image_io = BytesIO()
            image.save(image_io, format="PNG")
            image_io.seek(0)
            cached_image.write_bytes(image_io.getvalue())
            return await send_file(image_io, mimetype="image/png")
