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
from beanie import BulkWriter
from hashlib import md5
from ..utils.logger import l
from datetime import datetime, UTC, timedelta
from json import loads, dumps
from ..models.database.api import API


@tasks.loop(minutes=5)
async def update_mods_list():
    start = time.time()
    try:
        async with ClientSession() as session:
            async with session.get(
                f"https://trovesaurus.com/mods/api/list?token={os.getenv('TROVESAURUS_TOKEN')}"
            ) as response:
                data = await response.json()
                cache = ModCache()
                mod_directory = Path("mods")
                mod_files = [
                    file.stem for file in mod_directory.iterdir() if file.is_file()
                ]
                mod_searches = []
                mod_entries = []
                for i, mod in enumerate(data, 1):
                    ts_mod = TrovesaurusMod(**mod)
                    last_update = ts_mod.date
                    for d in ts_mod.files:
                        if d.date > last_update:
                            last_update = d.date
                    mod_searches.append(
                        SearchMod(
                            id=ts_mod.id,
                            name=ts_mod.name.lower(),
                            authors=[
                                author.Username.lower() for author in ts_mod.authors
                            ],
                            type=ts_mod.type,
                            sub_type=ts_mod.sub_type,
                            likes=ts_mod.likes,
                            views=ts_mod.views,
                            downloads=ts_mod.downloads,
                            last_update=last_update,
                        )
                    )
                    cache[mod["id"]] = ts_mod
                    for file in cache[mod["id"]].files:
                        if not file.hash:
                            l("Mod List").error(
                                f"Trovesaurus file {file.id} has no hash"
                            )
                            await session.get(
                                f"https://trovesaurus.com/client/pokehash.php?fileid={file.id}"
                            )
                            continue
                        # Crit can't fucking read
                        if file.format.lower() in ["zip", "tmod"]:
                            mod_entries.append(
                                ModEntry(
                                    hash=file.hash,
                                    name=ts_mod.name,
                                    format=file.format,
                                    description=ts_mod.description,
                                    authors=ts_mod.authors,
                                )
                            )
                            path = Path(f"mods/{file.hash}.{file.format}")
                            if file.hash not in mod_files:
                                req = f"https://trovesaurus.com/client/downloadfile.php?fileid={file.id}"
                                async with session.get(req) as file_response:
                                    file_data = await file_response.read()
                                    if md5(file_data).hexdigest() == file.hash:
                                        path.write_bytes(file_data)
                                    else:
                                        continue
                                        l("Mod List").error(
                                            f"Mod payload doesn't match hash: {file.hash}"
                                        )
                cache.process_hashes()
                current_app.mods_list = cache
                asyncio.create_task(offload_database_saves(mod_entries, mod_searches))
    except Exception as e:
        print(traceback.format_exc())
    print("Mods list updated in", time.time() - start, "seconds")


async def offload_database_saves(mod_entries, search_mods):
    for mod in mod_entries:
        await ModEntry.find_one(ModEntry.hash == mod.hash).update(
            {"$set": mod.model_dump(by_alias=True, exclude=["id"])}, upsert=True
        )
    for mod in search_mods:
        await SearchMod.find_one(SearchMod.id == mod.id).update(
            {"$set": mod.model_dump(by_alias=True, exclude=["id"])}, upsert=True
        )
    print("Mod list update task complete.")


@update_mods_list.before_loop
async def before_update_mods_list():
    l("Mod List").info("Mod list update task starting.")
    try:
        async for mod_entry in ModEntry.find_many({}):
            path = Path(f"mods/{mod_entry.hash}.{mod_entry.format}")
            if not path.exists():
                print(f"Mod {mod_entry.hash} not found in mods directory")
        print("Mod list check complete")
    except Exception as e:
        print(e)


@tasks.loop(minutes=10)
async def update_change_log():
    versions = []
    version_count = 10
    async with ClientSession() as session:
        async with session.get(
            "https://api.github.com/repos/AallynReed/RenewedTroveTools/releases",
            headers={
                "Authorization": "Bearer {}".format(os.getenv("GITHUB_TOKEN")),
            },
        ) as response:
            version_data = await response.json()
            for version in version_data[: version_count + 1]:
                versions.append((version["name"], version["published_at"]))
    changes = []
    change_log = {}
    for next, (version, published_at) in enumerate(versions[:version_count], 1):
        changes.append(
            (
                version,
                published_at,
                f"https://api.github.com/repos/AallynReed/RenewedTroveTools/compare/{versions[next][0]}...{version}",
            )
        )
    async with ClientSession() as session:
        for version, published_at, change in changes:
            async with session.get(
                change,
                headers={
                    "Authorization": "Bearer {}".format(os.getenv("GITHUB_TOKEN")),
                },
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


@tasks.loop(minutes=10)
async def get_versions():
    current_app.app_versions = []
    async with ClientSession() as session:
        i = 1
        while True:
            async with session.get(
                "https://api.github.com/repos/AallynReed/RenewedTroveTools/releases?per_page=100&page={}".format(
                    i
                ),
                headers={
                    "Authorization": "Bearer {}".format(os.getenv("GITHUB_TOKEN")),
                },
            ) as response:
                if response.status != 200:
                    break
                data = await response.json()
                current_app.app_versions.extend(data)
                if len(data) < 100:
                    break
                i += 1


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
            },
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
                "client_credentials",
            )
        ) as response:
            data = await response.json()
            current_app.twitch_credentials = (
                os.getenv("TWITCH_CLIENT_ID"),
                data["access_token"],
            )


@tasks.loop(minutes=180)
async def update_allies():
    print("Allies data fetch task starting.")
    async with ClientSession() as session:
        async with session.get(
            "https://trovesaurus.com/collection/Pets.json"
        ) as result:
            allies_list = await result.json()
            now = int(datetime.now(UTC).timestamp())
            i = 0
            x = 0
            y = 0
            z = 0
            old_allies = loads(open("versions/v1/data/allies.json").read())
            allies = loads(open("versions/v1/data/allies.json").read())
            found_allies = []
            for ally_item in allies_list:
                i += 1
                ally = ally_item.split("/")[-1]
                found_allies.append(ally)
                stop = False
                for data in old_allies.keys():
                    if ally == data:
                        if old_allies[data]["updated_at"] + 86400 * 7 > now:
                            stop = True
                            break
                if stop:
                    continue
                ally_result = await session.get(
                    "https://trovesaurus.com/collections/pet/" + ally + ".json"
                )
                ally_data = await ally_result.json()
                if ally in allies.keys():
                    old_ally = allies[ally]
                    ally_data["updated_at"] = old_ally["updated_at"]
                    if ally_data == old_ally:
                        continue
                    x += 1
                else:
                    z += 1
                ally_data["updated_at"] = now
                allies[ally] = ally_data
            to_delete = []
            for qualified_name in old_allies.keys():
                if qualified_name not in found_allies:
                    to_delete.append(qualified_name)
                    y += 1
            for dele in to_delete:
                del allies[dele]
            with open("versions/v1/data/allies.json", "w+") as f:
                f.write(dumps(allies, indent=4, sort_keys=True))
            print(
                f"Done - Checked: **{i}** | Updated: **{x}** | Removed: **{y}** | Added: **{z}**"
            )


# @tasks.loop(seconds=1)
# async def reset_biomes():
#     try:
#         print("Biomes reset task starting.")
#         api = await API.find_one({"_id": "api"})
#         print(api.biomes.current)
#         history_length = len(api.biomes.history)
#         now = datetime.now(UTC) - timedelta(hours=11)
#         gap = 60 * 60 * 3
#         begin_day = datetime(now.year, now.month, now.day, 0, 0, 0, 0, UTC)
#         time_day = now - begin_day
#         _, wait = divmod(time_day.total_seconds(), gap)
#         await asyncio.sleep(gap - wait + randint(0, 15))
#         api = await API.find_one({"_id": "api"})
#         if len(api.biomes.history) == history_length:
#             api.biomes.current.sort(key=lambda x: len(x[1]), reverse=True)
#             api.biomes.previous = [b for b, _ in api.biomes.current[:3]]
#             api.biomes.history.append(api.biomes.current)
#             api.biomes.current = []
#             await api.save()
#     except Exception as e:
#         print(traceback.format_exc())
#         print("Biomes reset task failed.")
