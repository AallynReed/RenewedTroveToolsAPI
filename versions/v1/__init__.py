from quart import Blueprint

from .mods import mods
from .star_chart import star
from .gem_builds import gem
from .profiles import profile_bp
from .user import user
from .image import image
from .stats import stats
from .misc import misc
from .market import market
from .leaderboards import leaderboards
from .rotations import rotations

api_v1 = Blueprint("api_v1", __name__, url_prefix="/v1", subdomain="kiwiapi")
# Register Endpoints
api_v1.register_blueprint(user)
api_v1.register_blueprint(star)
api_v1.register_blueprint(gem)
api_v1.register_blueprint(mods)
api_v1.register_blueprint(profile_bp)
api_v1.register_blueprint(image)
api_v1.register_blueprint(stats)
api_v1.register_blueprint(misc)
api_v1.register_blueprint(market)
api_v1.register_blueprint(leaderboards)
api_v1.register_blueprint(rotations)
