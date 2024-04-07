from dotenv import load_dotenv
from quart import Quart, request, jsonify
import os
from motor.motor_asyncio import AsyncIOMotorClient
import versions
from beanie import init_beanie
from versions.v1.models.database.star import StarBuild
from versions.v1.models.database.user import User
from versions.v1.models.database.mod import ModEntry, SearchMod
from versions.v1.models.database.profile import ModProfile
from versions.v1.models.database.gem import GemBuild
from versions.v1.models.database.api import API
import versions.v1.tasks as tasks
from flask_discord import DiscordOAuth2Session


config = {
    "DEBUG": True,
    "SERVER_NAME": "slynx.xyz"
}

app = Quart(__name__)
app.config.from_mapping(config)
app.register_blueprint(versions.api_v1)


load_dotenv()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.getenv("TOKEN").encode("utf-8")
app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")
app.config["DISCORD_BOT_TOKEN"] = os.getenv("DISCORD_BOT_TOKEN")


@app.before_serving
async def startup():
    app.environment_variables = os.environ
    client = AsyncIOMotorClient()
    tasks.update_mods_list.start()
    tasks.update_change_log.start()
    tasks.twitch_streams_fetch.start()
    await init_beanie(client.trove_api, document_models=[API, StarBuild, GemBuild, User, ModEntry, ModProfile, SearchMod])

# @app.before_request
# async def before_request():
#     print(request)


@app.route('/', subdomain="kiwiapi")
async def index():
    return "Welcome to the Trove API!"


@app.errorhandler(400)
async def bad_request(e):
    response = {
        "status_code": e.code,
        "type": "error",
    }
    response["message"] = e.description
    return jsonify(response), 400


@app.errorhandler(401)
async def unauthorized(e):
    response = {
        "status_code": e.code,
        "type": "error",
    }
    response["message"] = e.description
    return jsonify(response), 401


@app.errorhandler(403)
async def forbidden(e):
    response = {
        "status_code": e.code,
        "type": "error",
    }
    response["message"] = e.description
    return jsonify(response), 403


@app.errorhandler(404)
async def not_found(e):
    response = {
        "status_code": e.code,
        "type": "error",
    }
    response["message"] = e.description
    return jsonify(response), 404
