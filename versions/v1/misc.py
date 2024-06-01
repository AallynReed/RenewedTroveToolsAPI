from quart import Blueprint, request, abort, current_app, Response, send_file, redirect
from aiohttp import ClientSession
from os import getenv
import matplotlib.pyplot as plt
from io import BytesIO
import humanize
from .utils.discord import send_embed
import os
from datetime import datetime, UTC
import pycountry
from pathlib import Path
from base64 import b64encode
from utils import render_json
from versions.v1.models.database.api import API

misc = Blueprint("misc", __name__, url_prefix="/misc")
locales_folder = Path("versions/v1/locales")
assets_folder = Path("versions/v1/assets")


def format_number(number):
    if number < 0:
        return "-" + format_number(abs(number))
    if number >= 1000000:
        return (
            humanize.intword(number, format="%.2f")
            .replace(" ", "")
            .replace("million", "M")
        )
    elif number >= 1000:
        return (
            humanize.intword(number, format="%.2f")
            .replace(" ", "")
            .replace("thousand", "K")
        )
    else:
        return str(number)

@misc.route("/support")
async def support():
    return redirect("https://discord.gg/WTq6YxYzut")

@misc.route("/github")
async def github():
    return redirect("https://github.com/Sly0511/RenewedTroveTools")

@misc.route("/paypal")
async def paypal():
    return redirect("https://www.paypal.com/paypalme/waterin")

@misc.route("kofi")
async def kofi():
    return redirect("https://ko-fi.com/slydev")

@misc.route("bmc")
async def bmc():
    return redirect("https://www.buymeacoffee.com/sly1301")

@misc.route("/feedback", methods=["POST"])
async def feedback():
    data = await request.json
    message = data.get("message")
    if not message:
        return abort(400, "Missing message field.")
    embed = {
        "description": message,
    }

    payload = {"embeds": [embed]}
    async with ClientSession() as session:
        async with session.post(getenv("FEEDBACK_WEBHOOK"), json=payload) as resp:
            return Response(status=resp.status)


@misc.route("/change_log")
async def change_log():
    if not hasattr(current_app, "github_change_log"):
        return abort(503, "Change log is not available.")
    return render_json(current_app.github_change_log)


@misc.route("/twitch_streams")
async def streams():
    if not hasattr(current_app, "twitch_streams"):
        return abort(503, "Twitch streams are not available.")
    return render_json(current_app.twitch_streams)


@misc.route("/opn_chart")
async def opn_chart():
    plt.clf()
    plt.style.use("dark_background")
    fig, ax1 = plt.subplots()
    params = request.args
    forge_frag = int(params["forge_frag"])
    nitro_price = int(params["nitro_price"])
    nitro_sell = bool(int(params.get("nitro_sell", 0)))
    nitro_value = 175
    profit_points = {}
    market_cap = {}
    min_fpn = -300
    max_fpn = 601
    for uber in range(8, 12):
        m = [0, 0, 0, 0]
        c = [0, 0, 0, 0]
        i = 0
        x = 1000
        x_axis = []
        y_axis = []
        for z in range(100):
            nitro = nitro_value * (z + 1)
            i += x
            i += 1500 / (uber - 7) - forge_frag * (10 * (uber - 7) - 10)
            if nitro_sell:
                i += -nitro_value * nitro_price
            f_p_n = i / nitro
            if i < m[1]:
                m = [z + 1, i, nitro, f_p_n]
            if f_p_n < nitro_price:
                c = [z + 1, i, nitro, f_p_n]
            x_axis.append(f_p_n)
            y_axis.append(nitro)
            x += 2000
        profit_points[uber] = m
        market_cap[uber] = c
        ax1.plot(y_axis, x_axis, label=f"Uber {uber}")
    ax1.set_title("Chart for flux cost during refinements")
    ax1.axhline(y=0, color="green", linestyle="dashed", label="0 ea")
    ax1.axhline(
        y=nitro_price, color="red", linestyle="dashed", label=f"{nitro_price} ea"
    )
    ax2 = ax1.twiny()
    # ax3 = ax1.twinx()
    ax1.set_xticks(range(0, 17501, 1750))
    ax1.set_yticks(range(min_fpn, max_fpn, 100))
    ax2.set_xticks(range(-5, 106, 5))
    ax1.set_xlabel("Nitro obtained")
    ax1.set_ylabel("Flux per nitro (ea)")
    ax2.set_xlabel("Refinements done")
    # ax3.set_ylabel("Flux cost")
    ax2.grid(visible=True, axis="x", color="purple", linestyle="dashed")
    labels = ax2.get_xticklabels()
    labels[0] = labels[-1] = ""
    ax2.set_xticklabels(labels)
    # ax3labels = ax1.get_yticklabels()
    # ax3.set_yticks(range(0, 10))
    # for l in ax3labels:
    #     l.set_text(f"{int(l.get_text().replace('−', '-'))*17500:,}")
    # ax3.set_yticklabels(ax3labels)
    legend_1 = ax1.legend(loc=2, borderaxespad=1.0)
    legend_1.remove()
    legend_2 = ax2.legend(loc=2, borderaxespad=1.0)
    legend_2.remove()
    # ax3.legend(loc=1, borderaxespad=1.)
    ax2.add_artist(legend_1)
    # ax3.add_artist(legend_2)
    x_pf = [x[2] for x in profit_points.values()]
    y_pf = [x[3] for x in profit_points.values()]
    z_pf = [f"{x[0]} | {format_number(-x[1])}" for x in profit_points.values()]
    for i, txt in enumerate(z_pf):
        ax1.annotate(txt, (x_pf[i], y_pf[i]))
    x_mc = [x[2] for x in market_cap.values()]
    y_mc = [x[3] for x in market_cap.values()]
    z_mc = [
        f"{x[0]}\n{format_number(-x[1])}" for i, x in enumerate(market_cap.values())
    ]
    for i, txt in enumerate(z_mc):
        ax1.annotate(txt, (x_mc[i], y_mc[i]))
    data = BytesIO()
    plt.savefig(data, format="png", bbox_inches="tight", dpi=300)
    data.seek(0)
    return await send_file(data, mimetype="image/png")


@misc.route("/handshake")
async def handshake():
    if not hasattr(current_app, "app_versions"):
        return abort(503, "Latest release is not available.")
    headers = request.headers
    data = await request.json
    os_data = data.get("os", {})
    os_name = os_data.get("name", "Unknown")
    os_version = os_data.get("version", "")
    os_version = f"[{os_version}]" if os_version else ""
    os_release = os_data.get("release", "")
    country = headers.get("Cf-Ipcountry", None)
    if country:
        country = pycountry.countries.get(alpha_2=country)
        country = country.name
    else:
        country = "Unknown"
    update_version = None
    for version in current_app.app_versions:
        if update_version is not None:
            break
        for asset in version.get("assets"):
            asset_name = asset.get("name")
            if "debug" not in asset_name and asset_name.endswith(".msi"):
                update_version = version.get("tag_name")
                break
    await send_embed(
        os.getenv("APP_WEBHOOK"),
        {
            "title": "APP Launched",
            "description": "App has been launched",
            "color": 0x0000BB if data.get("version") == update_version else 0xBB0000,
            "fields": [
                {"name": "App Version", "value": data.get("version"), "inline": True},
                {
                    "name": "App Debug Mode",
                    "value": str(data.get("dev")),
                    "inline": True,
                },
                {"name": "Geolocation", "value": country},
                {
                    "name": "Operating System",
                    "value": f"{os_name} {os_release} {os_version}",
                },
            ],
        },
    )
    return "OK", 200


@misc.route("latest_version")
async def latest_version():
    if not hasattr(current_app, "app_versions"):
        return abort(503, "Latest version is not available.")
    for version in current_app.app_versions:
        for asset in version.get("assets"):
            asset_name = asset.get("name")
            if "debug" not in asset_name and asset_name.endswith(".msi"):
                return render_json({"version": version.get("tag_name")})
    return abort(404)


@misc.route("/latest_release")
async def latest_release():
    if not hasattr(current_app, "app_versions"):
        return abort(503, "Latest release is not available.")
    for version in current_app.app_versions:
        for asset in version.get("assets"):
            asset_name = asset.get("name")
            if "debug" not in asset_name and asset_name.endswith(".msi"):
                return render_json(version)
    return abort(404)


@misc.route("/latest_release/download")
async def latest_release_download():
    if not hasattr(current_app, "app_versions"):
        return abort(503, "Latest release is not available.")
    for version in current_app.app_versions:
        for asset in version.get("assets"):
            asset_name = asset.get("name")
            if "debug" not in asset_name and asset_name.endswith(".msi"):
                return {"download": asset.get("browser_download_url")}
    return abort(404, "No download link found.")


@misc.route("latest_release/download/redirect")
async def latest_release_download_redirect():
    if not hasattr(current_app, "app_versions"):
        return abort(503, "Latest release is not available.")
    headers = request.headers
    country = headers.get("Cf-Ipcountry", None)
    if country:
        country = pycountry.countries.get(alpha_2=country)
        country = country.name
    else:
        country = "Unknown"
    for version in current_app.app_versions:
        for asset in version.get("assets"):
            asset_name = asset.get("name")
            if "debug" not in asset_name and asset_name.endswith(".msi"):
                api = await API.find_one({"_id": "api"})
                api.downloads += 1
                await api.save()
                await send_embed(
                    os.getenv("APP_WEBHOOK"),
                    {
                        "title": "APP Downloaded",
                        "color": 0x00BB00,
                        "fields": [
                            {"name": "Geolocation", "value": country},
                        ],
                    },
                )
                return Response(
                    status=302, headers={"Location": asset.get("browser_download_url")}
                )
    return abort(404, "No download link found.")

@misc.route("/downloads_count")
async def downloads_count():
    api = await API.find_one({"_id": "api"})
    return render_json({"downloads": api.downloads})

@misc.route("/latest_release/debug")
async def latest_release_debug():
    if not hasattr(current_app, "app_versions"):
        return abort(503, "Latest release is not available.")
    for version in current_app.app_versions:
        for asset in version.get("assets"):
            asset_name = asset.get("name")
            if "debug" in asset_name and asset_name.endswith(".msi"):
                return {"download": asset.get("browser_download_url")}
    return abort(404, "No download link found.")


@misc.route("latest_release/debug/redirect")
async def latest_release_debug_redirect():
    if not hasattr(current_app, "app_versions"):
        return abort(503, "Latest release is not available.") 
    for version in current_app.app_versions:
        for asset in version.get("assets"):
            asset_name = asset.get("name")
            if "debug" in asset_name and asset_name.endswith(".msi"):
                return Response(
                    status=302, headers={"Location": asset.get("browser_download_url")}
                )
    return abort(404, "No download link found.")


# @misc.route("sage_dump")
# async def sage_dump():
#     return render_json(
#         await current_app.database_client["trove"]["tags"]
#         .find({})
#         .to_list(length=99999)
#     )


@misc.route("/locales", methods=["GET"])
async def get_locales():
    files = {}
    for x in locales_folder.rglob("*.loc"):
        if x.is_file():
            fix_file = []
            with open(x) as f:
                data = f.read()
                for l in data.splitlines():
                    if not l:
                        continue
                    split = l.split("»»", 1)
                    if len(split) != 2:
                        continue
                    k, v = split
                    if k and v:
                        fix_file.append((k, v))
            fix_file = "\n".join([f"{k}»»{v}" for k, v in sorted(list(set(fix_file)), key=lambda x: x[0])])
            x.write_text(fix_file)
            file_name = str(x.relative_to(locales_folder).as_posix())
            files[file_name] = b64encode(x.read_bytes()).decode("utf-8")
    return render_json(files)


@misc.route("/assets/<path:subpath>", methods=["GET"])
async def get_assets(subpath):
    file = assets_folder.joinpath(subpath)
    if not file.exists():
        return abort(404)
    return await send_file(file, mimetype="image/png")
