from quart import current_app, Blueprint, request, render_template
from website.internals.models.trove.gem_builds import GemBuildConfig, Class, BuildType


gems = Blueprint("gem_builds", __name__)


@gems.route("/gem_builds", methods=["GET"])
async def gem_builds():
    config = GemBuildConfig()
    return await render_template(
        "app/gem_builds.html",
        config=config.dict(),
        classes=list(Class),
        build_types=list(BuildType),
    )
