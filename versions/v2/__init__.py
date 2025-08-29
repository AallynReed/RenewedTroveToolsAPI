from quart import Blueprint

from .gems import gems


api_v2 = Blueprint("api_v2", __name__, url_prefix="/v2", subdomain="kiwiapi")
# Register Endpoints
api_v2.register_blueprint(gems)
