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
                    search_mod = SearchMod(
                        id=ts_mod.id,
                        name=ts_mod.name.lower(),
                        authors=[author.Username.lower() for author in ts_mod.authors],
                        type=ts_mod.type,
                        sub_type=ts_mod.sub_type,
                        likes=ts_mod.likes,
                        views=ts_mod.views,
                        downloads=ts_mod.downloads,
                    )
                    await SearchMod.find_one(SearchMod.id == ts_mod.id).update({"$set": search_mod.model_dump(by_alias=True, exclude=["id"])}, upsert=True)
                    cache[mod["id"]] = ts_mod
                    for file in cache[mod["id"]].files:
                            if not file.hash:
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

