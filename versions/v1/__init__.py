from quart import Blueprint, request, jsonify, current_app, abort
from .star_chart import star
from .mods import mods
from .user import user


api_v1 = Blueprint('api_v1', __name__, url_prefix='/v1')
# Register Endpoints
api_v1.register_blueprint(star)
api_v1.register_blueprint(mods)
api_v1.register_blueprint(user)


@api_v1.route('/')
async def index():
    return "Renewed Trove Tools API v1"



