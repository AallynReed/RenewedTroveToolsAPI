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
from versions.v1.models.database.market import MarketListing
from versions.v1.models.database.leaderboards import LeaderboardEntry
import versions.v1.tasks as tasks
from flask_discord import DiscordOAuth2Session
from versions.v1.utils.logger import Logger
from pathlib import Path
from datetime import datetime, UTC, timedelta
from copy import deepcopy
from aiohttp import ClientSession
from utils import render_json, render
from quart_cors import cors
import re
from humanize import precisedelta
from website.internals.models import data
from yaml import safe_load
from website.internals.app import kiwiapp
import redis
from json import loads, dumps
import pickle

config = {
    "DEBUG": True,
    "SERVER_NAME": "aallyn.xyz",
    "MAX_CONTENT_LENGTH": 300 * 1024 * 1024,
}

app = Quart(__name__, template_folder="website", static_folder="website")
app.config.from_mapping(config)
app = cors(app, allow_origin=re.compile(r"https:\/\/(\w+\.)?aallyn\.xyz"))
app.register_blueprint(versions.api_v1)
app.register_blueprint(kiwiapp)

try:
    from personal import personal_bp

    app.register_blueprint(personal_bp)
except ImportError:
    pass


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


def get_from_redis(key):
    value = app.redis.get(key)
    if value is None:
        return value
    return loads(value.decode("utf-8"))


def set_to_redis(key, value):
    return app.redis.set(key, dumps(value))


def get_object_from_redis(key):
    value = app.redis.get(key)
    if value is None:
        return value
    return pickle.loads(value)


def set_object_to_redis(key, value):
    return app.redis.set(key, pickle.dumps(value))


@app.before_serving
async def startup():
    setup_loggers()
    app.environment_variables = os.environ
    client = AsyncIOMotorClient(port=27018)
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
            MarketListing,
            LeaderboardEntry
        ],
    )
    # tasks.twitch_streams_fetch.start()
    # tasks.reset_biomes.start()
    app.redis = redis.Redis(host="localhost", port=6379)
    app.get_from_redis = get_from_redis
    app.set_to_redis = set_to_redis
    app.get_object_from_redis = get_object_from_redis
    app.set_object_to_redis = set_object_to_redis
    main_worker = app.redis.get("main_worker")
    app.main_worker = False
    if main_worker is not None:
        main_worker = datetime.fromtimestamp(int(main_worker), UTC)
        if (datetime.now(UTC) - main_worker).total_seconds() > 5:
            app.redis.set("main_worker", int(datetime.now(UTC).timestamp()))
            app.redis.delete("change_log", "app_versions", "mods_cache", "mods_cache_updated")
            app.main_worker = True
            tasks.update_change_log.start()
            tasks.get_versions.start()
            tasks.update_allies.start()
    else:
        app.redis.set("main_worker", int(datetime.now(UTC).timestamp()))
        app.redis.delete("change_log", "app_versions", "mods_cache", "mods_cache_updated")
        app.main_worker = True
        tasks.update_change_log.start()
        tasks.get_versions.start()
        tasks.update_allies.start()
    tasks.update_mods_list.start()


# @app.before_request
# async def before_request():
#     print(dict(request.headers))


@app.route("/favicon.ico")
@app.route("/favicon.ico", subdomain="trove")
@app.route("/favicon.ico", subdomain="kiwiapi")
@app.route("/favicon.ico", subdomain="app")
async def favicon():
    return await app.send_static_file("assets/favicon.ico")


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


@app.route("/data/<path:path>")
@app.route("/data/<path:path>", subdomain="trove")
async def send_data(path):
    return await app.send_static_file(f"data/{path}")


@app.route("/")
@app.route("/", subdomain="trove")
async def home():
    features = [
        {
            "name": "Timers",
            "description": "Check daily, weekly, luxion, corruxion and other timers with ease at a glance.",
            "app": False,
            "icon": "timer",
        },
        {
            "name": "Live Stats",
            "description": "Be sure that in-game stats will be updated as soon as possible.",
            "app": False,
            "icon": "query_stats",
        },
        {
            "name": "Events",
            "description": "Be up to date with the new events on Trove and Trovesaurus.",
            "app": False,
            "icon": "event",
        },
        {
            "name": "Twitch Tracker",
            "description": "Find new Trove streamers to watch and engage with.",
            "app": False,
            "icon": "tv",
        },
        {
            "name": "Mod Profiles (Soon)",
            "description": "Profile presets for mods.",
            "app": True,
            "icon": "timer",
        },
        {
            "name": "Mod Manager",
            "description": "Manage your mods with ease and update them at will.",
            "app": True,
            "icon": "extension",
        },
        {
            "name": "Modder Tools",
            "description": "Create your own mods and compile them with ease.",
            "app": True,
            "icon": "construction",
        },
        {
            "name": "Mod Projects",
            "description": "Keep your projects clean and organized with mod projects.",
            "app": True,
            "icon": "account_tree",
        },
        {
            "name": "Game Files Extractor",
            "description": "Extract game files efficiently and quickly compared to the game client.",
            "app": True,
            "icon": "unarchive",
        },
        {
            "name": "Star Chart",
            "description": "Test your star chart builds quickly and easily before spending resources.",
            "app": False,
            "icon": "stars",
        },
        {
            "name": "Gem Builds",
            "description": "Max out your class with customizable gem builds with a powerful calculator.",
            "app": False,
            "icon": "timer",
        },
        {
            "name": "Gear Builds",
            "description": "Make sure to optimize your class's equipments to your playstyle.",
            "app": False,
            "icon": "shield",
        },
        {
            "name": "Gem Simulator",
            "description": "Learn how gems work and test them with this 1:1 gem simulator.",
            "app": False,
            "icon": "science",
        },
        {
            "name": "Gem Set Calculator",
            "description": "Check the maxed ouot stats of your gems before even getting them.",
            "app": False,
            "icon": "diamond",
        },
        {
            "name": "Mastery",
            "description": "See what stats await you at each mastery level.",
            "app": False,
            "icon": "menu_book",
        },
        {
            "name": "Magic Find",
            "description": "Calculate your magic find with this calculator.",
            "app": False,
            "icon": "menu_book",
        },
    ]
    features = [features[i : i + 4] for i in range(0, len(features), 4)]
    previews = [
        "assets/previews/" + path.name
        for path in Path("website/assets/previews").rglob("*")
        if path.is_file()
    ]
    previews.sort()
    previews = list(enumerate(previews))
    return await render("index.html", features=features, previews=previews)


@app.route("/long_shade_rotation")
@app.route("/long_shade_rotation", subdomain="trove")
async def redirect_long_shade_rotation():
    return redirect("https://app.aallyn.xyz/long_shade_rotation")

@app.route("/long_shade_rotation", subdomain="app")
async def long_shade_rotation():
    advanced = "advanced" in request.args
    async with ClientSession() as session:
        async with session.get(
            "https://kiwiapi.aallyn.xyz/v1/misc/d15_biomes"
        ) as response:
            biomes_rotation = await response.json()
            history = biomes_rotation["history"]
            now = datetime.now(UTC)
            biomes = []
            for i, (start, _, f, s, t, current) in enumerate(history):
                biomes.extend([f["biome"], s["biome"], t["biome"]])
                start = datetime.fromtimestamp(start, UTC)
                start = (now - start).total_seconds()
                history[i][0] = [
                    precisedelta(
                        timedelta(seconds=start),
                        minimum_unit="minutes",
                        suppress=["days"],
                        format="%0.f",
                    ),
                    int((now.timestamp() - start) * 1000),
                ]
                if start > 0:
                    history[i][0][0] = history[i][0][0] + " ago"
                history[i][0][0] = (
                    history[i][0][0]
                    .replace(" minutes", "m")
                    .replace(" hours", "h")
                    .replace(" minute", "m")
                    .replace(" hour", "h")
                    .replace(" and ", ", ")
                )
                if current:
                    history[i][0] = ["Happening now", int(now.timestamp() * 1000)]
            biomes = list(set(biomes))
            biomes_list = []
            for biome in biomes:
                for start, end, f, s, t, current in history:
                    for b in [f, s, t]:
                        bb = [
                            b["name"] if advanced else b["final_name"],
                            b["icon"],
                            b["biome"],
                        ]
                        if bb not in biomes_list and b["biome"] == biome:
                            biomes_list.append(bb)
            biomes_list.sort(key=lambda x: x[0])
            biome_icons = list(set([b[1] for b in biomes_list]))
            biome_icons.sort()
            return await render(
                "long_shade_rotation.html",
                biomes=biomes_list,
                biome_icons=biome_icons,
                history=history,
                advanced=advanced,
            )
    return abort(503, "Service is unavailable.")


@app.route("/lootboxes/<lootbox>")
@app.route("/lootboxes/<lootbox>", subdomain="trove")
async def redirect_lootbox(lootbox):
    return redirect(f"https://app.aallyn.xyz/lootboxes/{lootbox}")

@app.route("/lootboxes/<lootbox>", subdomain="app")
async def lootbox(lootbox):
    lootboxes_path = Path("website/data/lootboxes")
    for lootbox_file in lootboxes_path.rglob("*.yaml"):
        if lootbox_file.is_file():
            lootbox_data = safe_load(lootbox_file.read_text())
            lb = data.Webpage.parse_obj(lootbox_data)
            if lb.webpage == lootbox:
                loot_tables = data.Table(data=lb)
                return await render(
                    "lootbox.html", lootbox=lb, tables=loot_tables.tables
                )
    return abort(404, "Lootbox not found.")


@app.route("/testing_grounds")
@app.route("/testing_grounds", subdomain="trove")
async def testing_grounds():
    return await render("testing_grounds.html")


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
    change_log = app.get_from_redis("change_log")
    if change_log is None:
        return abort(503, "Change log is not available.")
    change_log = [
        {"version": version, "change": change}
        for version, change in sorted(
            change_log.items(),
            key=lambda x: ".".join([f"{int(i):02d}" for i in x[0].split(".")]),
            reverse=True,
        )
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
