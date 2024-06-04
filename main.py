from dotenv import load_dotenv
from quart import Quart, request, abort, make_response, redirect
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
from versions.v1.utils.logger import Logger
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from aiohttp import ClientSession
from utils import render_json, render
from quart_cors import cors
import re

config = {
    "DEBUG": True,
    "SERVER_NAME": "aallyn.xyz",
    "MAX_CONTENT_LENGTH": 300 * 1024 * 1024,
}

app = Quart(__name__, template_folder="website", static_folder="website")
app.config.from_mapping(config)
app = cors(app, allow_origin=re.compile(r"https:\/\/(.*\.)?aallyn\.xyz"))
app.register_blueprint(versions.api_v1)


load_dotenv()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.getenv("TOKEN").encode("utf-8")
app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")
app.config["DISCORD_BOT_TOKEN"] = os.getenv("DISCORD_BOT_TOKEN")


def setup_loggers():
    Logger("Mod List")


@app.before_serving
async def startup():
    setup_loggers()
    app.environment_variables = os.environ
    client = AsyncIOMotorClient()
    app.database_client = client
    await init_beanie(
        client.trove_api,
        document_models=[
            API,
            StarBuild,
            GemBuild,
            User,
            ModEntry,
            ModProfile,
            SearchMod,
        ],
    )
    tasks.update_mods_list.start()
    tasks.update_change_log.start()
    tasks.get_versions.start()
    tasks.twitch_streams_fetch.start()

# @app.before_request
# async def before_request():
#     print((request.headers)["Cf-Connecting-IP"])

@app.route("/css/<path:path>")
@app.route("/css/<path:path>", subdomain="trove")
async def send_css(path):
    return await app.send_static_file(f"css/{path}")

@app.route("/js/<path:path>")
@app.route("/js/<path:path>", subdomain="trove")
async def send_js(path):
    return await app.send_static_file(f"js/{path}")

@app.route("/assets/<path:path>")
@app.route("/assets/<path:path>", subdomain="trove")
async def send_assets(path):
    return await app.send_static_file(f"assets/{path}")

@app.route("/")
@app.route("/", subdomain="trove")
async def home():
    features = [
        {"name": "Timers", "description": "Check daily, weekly, luxion, corruxion and other timers with ease at a glance.", "app": False, "icon": "timer"},
        {"name": "Live Stats", "description": "Be sure that in-game stats will be updated as soon as possible.", "app": False, "icon": "query_stats"},
        {"name": "Events", "description": "Be up to date with the new events on Trove and Trovesaurus.", "app": False, "icon": "event"},
        {"name": "Twitch Tracker", "description": "Find new Trove streamers to watch and engage with.", "app": False, "icon": "tv"},
        {"name": "Mod Profiles (Soon)", "description": "Profile presets for mods.", "app": True, "icon": "timer"},
        {"name": "Mod Manager", "description": "Manage your mods with ease and update them at will.", "app": True, "icon": "extension"},
        {"name": "Modder Tools", "description": "Create your own mods and compile them with ease.", "app": True, "icon": "construction"},
        {"name": "Mod Projects", "description": "Keep your projects clean and organized with mod projects.", "app": True, "icon": "account_tree"},
        {"name": "Game Files Extractor", "description": "Extract game files efficiently and quickly compared to the game client.", "app": True, "icon": "unarchive"},
        {"name": "Star Chart", "description": "Test your star chart builds quickly and easily before spending resources.", "app": False, "icon": "stars"},
        {"name": "Gem Builds", "description": "Max out your class with customizable gem builds with a powerful calculator.", "app": False, "icon": "timer"},
        {"name": "Gear Builds", "description": "Make sure to optimize your class's equipments to your playstyle.", "app": False, "icon": "shield"},
        {"name": "Gem Simulator", "description": "Learn how gems work and test them with this 1:1 gem simulator.", "app": False, "icon": "science"},
        {"name": "Gem Set Calculator", "description": "Check the maxed ouot stats of your gems before even getting them.", "app": False, "icon": "diamond"},
        {"name": "Mastery", "description": "See what stats await you at each mastery level.", "app": False, "icon": "menu_book"},
        {"name": "Magic Find", "description": "Calculate your magic find with this calculator.", "app": False, "icon": "menu_book"}
    ]
    features = [features[i:i + 4] for i in range(0, len(features), 4)]
    previews = [
        "assets/previews/" + path.name
        for path in Path("website/assets/previews").rglob("*") if path.is_file()
    ]
    previews.sort()
    previews = list(enumerate(previews))
    return await render("index.html", features=features, previews=previews)

@app.route("/privacy")
@app.route("/privacy", subdomain="trove")
async def privacy():
    return await render("privacy.html")

@app.route("/terms")
@app.route("/terms", subdomain="trove")
async def terms():
    return await render("terms.html")

@app.route("/donate")
@app.route("/donate", subdomain="trove")
async def donate():
    return await render("donate.html")

@app.route("/change_log")
@app.route("/change_log", subdomain="trove")
async def change_log():
    if not hasattr(app, "github_change_log"):
        return abort(503, "Change log is not available.")
    change_log = deepcopy(app.github_change_log)
    change_log = [
        {"version": version, "change": change}
        for version, change in sorted(change_log.items(), key=lambda x: ".".join([f"{int(i):02d}" for i in x[0].split(".")]), reverse=True)
    ]
    for change in change_log:
        date = datetime.fromisoformat(change["change"]["time"])
        change["change"]["time"] = date.strftime("%d %B %Y")
        for c in change["change"]["commits"]:
            d = datetime.fromisoformat(c["date"])
            c["date"] = d.strftime("%d %B %Y")
            c["id"] = c["url"].split("/")[-1][:7]
        change["change"]["commits"].reverse()
    return await render("change_log.html", change_log=change_log)

@app.route("/documentation")
@app.route("/documentation", subdomain="trove")
async def documentation():
    return await render("documentation.html")


@app.route("/.well-known/discord")
async def aallyn_discord_link():
    return "dh=d9f4e6ed8eb40bacb2cb35f3444e9aca4a6bac05"


@app.route("/.well-known/discord", subdomain="kiwiapi")
async def kiwi_discord_link():
    return "dh=c712e1d862b981c8af888cde0f547a7799d6ae82"


@app.route("/", subdomain="kiwiapi")
async def index():
    return "Welcome to the Trove API!"


@app.errorhandler(400)
async def bad_request(e):
    response = {
        "status_code": e.code,
        "type": "error",
    }
    response["message"] = e.description
    return render_json(response), 400


@app.errorhandler(401)
async def unauthorized(e):
    response = {
        "status_code": e.code,
        "type": "error",
    }
    response["message"] = e.description
    return render_json(response), 401


@app.errorhandler(403)
async def forbidden(e):
    response = {
        "status_code": e.code,
        "type": "error",
    }
    response["message"] = e.description
    return render_json(response), 403


@app.errorhandler(404)
async def not_found(e):
    response = {
        "status_code": e.code,
        "type": "error",
    }
    response["message"] = e.description
    return render_json(response), 404
