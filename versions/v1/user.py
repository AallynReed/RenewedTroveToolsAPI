from quart import (
    Blueprint,
    url_for,
    session,
    request,
    redirect,
    abort,
    render_template,
)
from requests_oauthlib import OAuth2Session
import os
import traceback
from .models.database.user import User
from datetime import datetime, UTC
from beanie import PydanticObjectId
from aiohttp import ClientSession
from random import randint
from .utils.discord import send_embed
from utils import render_json
from quart_cors import cors

user = Blueprint("user", __name__, url_prefix="/user", template_folder="templates")

API_BASE_URL = "https://discord.com/api"
TOKEN_URL = API_BASE_URL + "/oauth2/token"
AUTHORIZATION_BASE_URL = API_BASE_URL + "/oauth2/authorize"


@user.route("/")
async def index():
    return "User API"


@user.route("/discord", methods=["GET"])
async def get_discord_user():
    return "Discord User API"


async def token_updater(token):
    session["oauth2_token"] = token


async def make_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=os.getenv("DISCORD_CLIENT_ID"),
        token=token,
        state=state,
        scope=scope,
        redirect_uri=os.getenv("DISCORD_REDIRECT_URI"),
        auto_refresh_kwargs={
            "client_id": os.getenv("DISCORD_CLIENT_ID"),
            "client_secret": os.getenv("DISCORD_CLIENT_SECRET"),
        },
        auto_refresh_url=TOKEN_URL,
        token_updater=await token_updater(token),
    )


@user.route("/discord/login")
async def oauth():
    scope = request.args.get("scope", "identify")
    usession = await make_session(scope=scope.split(" "))
    authorization_url, state = usession.authorization_url(AUTHORIZATION_BASE_URL)
    session["oauth2_state"] = state
    session["next"] = request.args.get("next", "/")
    return redirect(authorization_url)


@user.route("/discord/login/callback", methods=["GET"])
async def authorize():
    if (await request.values).get("error"):
        return request.values["error"]
    try:
        usession = await make_session(state=session.get("oauth2_state"))
        token = usession.fetch_token(
            TOKEN_URL,
            client_secret=os.getenv("DISCORD_CLIENT_SECRET"),
            authorization_response=request.url,
        )

        session["oauth2_token"] = token
        user = usession.get(API_BASE_URL + "/users/@me").json()

    except Exception as e:
        print("\n".join(traceback.format_exception(type(e), e, e.__traceback__)))
        return "Failed to login, try again."

    db_user = await User.find_one({"discord_id": int(user["id"])})
    if db_user is None:
        print("User not found")
        try:
            db_user = User(
                discord_id=int(user["id"]),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                last_login=datetime.now(UTC),
                username=user["username"],
                name=user["global_name"],
                avatar_hash=user["avatar"],
            )
            await db_user.save()
            await send_embed(
                os.getenv("USER_WEBHOOK"),
                {
                    "title": "User Registered",
                    "description": f"<:discord:1232031240329232444> User **{db_user.username}** has registered.",
                    "color": 0x00FF00,
                },
            )
        except KeyError:
            return "Failed to login, try again."
    else:
        db_user.last_login = datetime.now(UTC)
        db_user.username = user["username"]
        db_user.name = user["global_name"]
        db_user.avatar_hash = user["avatar"]
        db_user.updated_at = datetime.now(UTC)
        await db_user.save()
    return redirect(
        url_for("api_v1.user.get_discord_me") + "?pass_key=" + str(db_user.id)
    )


@user.route("/discord/reset_token", methods=["GET"])
async def reset_token():
    params = request.args
    token = params.get("token")
    if token is None:
        return abort(400, "No pass key provided.")
    db_user = await User.find_one({"internal_token": token})
    if db_user is None:
        return abort(404, "User not found.")
    else:
        db_user.reset_token()
        await db_user.save()
    return redirect(
        url_for("api_v1.user.get_discord_me") + "?pass_key=" + str(db_user.id)
    )


@user.route("/discord/me/", methods=["GET"])
async def get_discord_me():
    params = request.args
    token = params.get("pass_key")
    if token is None:
        return abort(400, "No pass key provided.")
    user = await User.find_one(User.id == PydanticObjectId(token))
    if not user:
        return abort(404, "User not found.")
    return await render_template("user.html", user=user)


@user.route("/discord/get", methods=["GET"])
async def get_user():
    params = request.args
    user_token = params.get("pass_key")
    if user_token is None:
        return abort(400, "No pass key provided.")
    user = await User.find_one(User.internal_token == user_token)
    if not user:
        async with ClientSession() as session:
            async with session.get(
                f"https://trovesaurus.com/client/useridfromkey.php?key={user_token}",
                allow_redirects=True,
            ) as response:
                if response.status != 200:
                    return abort(404, "User not found.")
                data = await response.json()
                user = await User.find_one(User.discord_id == int(data["user_id"]))
                if user:
                    user.internal_token = user_token
                    user.name = data["username"]
                    user.username = data["username"]
                    avatar_hash = (
                        data["custom_profile_image"]
                        or data["icon"]
                        or None
                    )
                    await user.save()
                else:
                    user = User(
                        internal_token=user_token,
                        discord_id=int(data["user_id"]),
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                        last_login=datetime.now(UTC),
                        username=data["username"],
                        name=data["username"],
                        avatar_hash=data["custom_profile_image"]
                        or data["icon"]
                        or None,
                    )
                    await user.save()
                    await send_embed(
                        os.getenv("USER_WEBHOOK"),
                        {
                            "title": "User Registered",
                            "description": f"<:trovesaurus:1232031134142042112> User **{user.username}** has registered.",
                            "color": 0x00FF00,
                        },
                    )
        user = await User.find_one(User.internal_token == user_token)
    user.last_login = datetime.now(UTC)
    await user.save()
    data = user.dict()
    data["avatar_url"] = user.avatar_url
    if user.discord_id < 100_000_000:
        icon = "<:trovesaurus:1232031134142042112>"
        async with ClientSession() as session:
            async with session.get(
                f"https://trovesaurus.com/client/useridfromkey.php?key={user_token}",
                allow_redirects=True,
            ) as response:
                if response.status != 200:
                    return abort(404, "User not found.")
                tdata = await response.json()
                user.internal_token = user_token
                user.name = tdata["username"]
                user.username = tdata["username"]
                avatar_hash = (
                    tdata["custom_profile_image"]
                    or tdata["icon"]
                    or None
                )
                await user.save()
    else:
        icon = "<:discord:1232031240329232444>"
    await send_embed(
        os.getenv("USER_WEBHOOK"),
        {
            "title": "User Logged in",
            "description": f"{icon} [{user.discord_id}] **{user.username}** has logged in.",
            "color": 0x0000FF,
        },
    )
    return render_json(data)
