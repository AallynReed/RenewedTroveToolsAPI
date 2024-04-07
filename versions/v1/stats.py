from quart import Blueprint, request, abort, jsonify, current_app, send_file, Response
from PIL import Image
from enum import Enum
from aiohttp import ClientSession
from io import BytesIO
from pathlib import Path
from hashlib import md5
from versions.v1.models.database.api import API

stats = Blueprint('stats', __name__, url_prefix='/stats')
stats_folder = Path('versions/v1/data')

@stats.route('/file/<path:u_path>', methods=['GET'])
async def file(u_path):
    file = stats_folder.joinpath(u_path)
    if file.exists():
        return await send_file(file)
    else:
        return abort(404)
    
@stats.route('/files', methods=['GET'])
async def files():
    return jsonify([str(x.relative_to(stats_folder)) for x in stats_folder.rglob('*') if x.is_file()])

@stats.route('/mastery', methods=['GET'])
async def mastery():
    return jsonify((await API.find_one({"_id": "api"})).dict()["mastery"])