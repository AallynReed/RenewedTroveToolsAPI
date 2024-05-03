from quart import current_app
from ..utils import tasks
from aiohttp import ClientSession
from ..utils.trovesaurus import TrovesaurusMod
from ..models.database.mod import ModEntry, SearchMod
from ..utils.cache import ModCache
from pathlib import Path
import os
from random import randint
import asyncio
import traceback
import time


@tasks.loop(minutes=30)
async def update_mods_list():
    start = time.time()
    try:
        async with ClientSession() as session:
            async with session.get(f"https://trovesaurus.com/mods/api/list?token={os.getenv('TROVESAURUS_TOKEN')}") as response:
                data = await response.json()
                cache = ModCache()
                mod_directory = Path("mods")
                mod_files = [file.stem for file in mod_directory.iterdir() if file.is_file()]
                for i, mod in enumerate(data, 1):
                    ts_mod = TrovesaurusMod(**mod)
                    last_update = ts_mod.date
                    for d in ts_mod.files:
                        if d.date > last_update:
                            last_update = d.date
                    search_mod = SearchMod(
                        id=ts_mod.id,
                        name=ts_mod.name.lower(),
                        authors=[author.Username.lower() for author in ts_mod.authors],
                        type=ts_mod.type,
                        sub_type=ts_mod.sub_type,
                        likes=ts_mod.likes,
                        views=ts_mod.views,
                        downloads=ts_mod.downloads,
                        last_update=last_update,
                    )
                    await SearchMod.find_one(SearchMod.id == ts_mod.id).update({"$set": search_mod.model_dump(by_alias=True, exclude=["id"])}, upsert=True)
                    cache[mod["id"]] = ts_mod
                    for file in cache[mod["id"]].files:
                        if not file.hash:
                            print(file.id, "has no hash")
                            async with session.get(f"https://trovesaurus.com/client/pokehash.php?fileid={file.id}") as response:
                                ...
                            continue
                        ts_entry = ModEntry(
                            hash=file.hash,
                            name=ts_mod.name,
                            format=file.format,
                            description=ts_mod.description,
                            authors=ts_mod.authors,
                        )
                        await ModEntry.find_one(ModEntry.hash == file.hash).update({"$set": ts_entry.model_dump(by_alias=True, exclude=["id"])}, upsert=True)
                        path = Path(f"mods/{file.hash}.{file.format}")
                        if file.hash not in mod_files:
                            req = f"https://trovesaurus.com/client/downloadfile.php?fileid={file.id}"
                            async with session.get(req) as file_response:
                                file_data = await file_response.read()
                                path.write_bytes(file_data)
                cache.process_hashes()
                current_app.mods_list = cache
    except Exception as e:
        print(f"Failed to update mods list:")
        print(traceback.format_exc())
    print("Mods list updated in", time.time() - start, "seconds")
    await asyncio.sleep(randint(60, 300))

@update_mods_list.before_loop
async def before_update_mods_list():
    await asyncio.sleep(randint(0, 15))
    print("Mods list update task starting.")


@tasks.loop(minutes=10)
async def update_change_log():
    versions = []
    version_count = 5
    async with ClientSession() as session:
        async with session.get(
            "https://api.github.com/repos/Sly0511/RenewedTroveTools/releases",
            headers={
                "Authorization": "Bearer {}".format(os.getenv("GITHUB_TOKEN")),
            }
        ) as response:
            version_data = await response.json()
            for version in version_data[:version_count + 1]:
                versions.append(
                    (
                        version["name"],
                        version["published_at"]
                    )
                )
    changes = []
    change_log = {}
    for next, (version, published_at) in enumerate(versions[:version_count], 1):
        changes.append(
            (
                version,
                published_at,
                f"https://api.github.com/repos/Sly0511/RenewedTroveTools/compare/{versions[next][0]}...{version}"
            )
        )
    async with ClientSession() as session:
        for version, published_at, change in changes:
            async with session.get(
                change, 
                headers={
                    "Authorization": "Bearer {}".format(os.getenv("GITHUB_TOKEN")),
                }
            ) as response:
                change_data = await response.json()
                for commit in change_data["commits"]:
                    message = commit["commit"]["message"]
                    if "upped" in message.lower():
                        continue
                    if version not in change_log:
                        change_log[version] = {"commits": [], "time": published_at}
                    change_log[version]["commits"].append(
                        {
                            "message": message,
                            "author": commit["commit"]["author"]["name"],
                            "url": commit["html_url"],
                            "date": commit["commit"]["author"]["date"],
                        }
                    )
    current_app.github_change_log = change_log

@update_change_log.before_loop
async def before_update_change_log():
    print("Change log update task starting.")

@tasks.loop(minutes=5)
async def get_versions():
    async with ClientSession() as session:
        async with session.get(
            "https://api.github.com/repos/Sly0511/RenewedTroveTools/releases"
        ) as response:
            try:
                current_app.app_versions = await response.json()
            except:
                current_app.app_versions = []

@get_versions.before_loop
async def before_get_versions():
    print("Versions fetch task starting.")

@tasks.loop(minutes=5)
async def twitch_streams_fetch():
    async with ClientSession() as session:
        async with session.get(
            f"https://api.twitch.tv/helix/streams?game_id=412756&first=100",
            headers={
                "Client-Id": current_app.twitch_credentials[0],
                "Authorization": f"Bearer {current_app.twitch_credentials[1]}",
            }
        ) as response:
            data = await response.json()
            current_app.twitch_streams = data["data"]

@twitch_streams_fetch.before_loop
async def before_twitch_streams_fetch():
    print("Twitch streams fetch task starting.")
    async with ClientSession() as session:
        async with session.post(
            "https://id.twitch.tv/oauth2/token?client_id={}&client_secret={}&grant_type={}".format(
                os.getenv("TWITCH_CLIENT_ID"),
                os.getenv("TWITCH_CLIENT_SECRET"),
                "client_credentials"
            )
        ) as response:
            data = await response.json()
            current_app.twitch_credentials = os.getenv("TWITCH_CLIENT_ID"), data["access_token"]