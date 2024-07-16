from quart import Blueprint

from .gem_builds import gems


kiwiapp = Blueprint("kiwiapp", __name__, subdomain="app")

kiwiapp.register_blueprint(gems)
