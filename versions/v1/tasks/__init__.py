from quart import current_app
from ..utils import tasks
from aiohttp import ClientSession
from ..utils.trovesaurus import TrovesaurusMod
from ..models.database.mod import ModEntry
from ..utils.cache import ModCache
from pathlib import Path


@tasks.loop(minutes=30)
async def update_mods_list():
    async with ClientSession() as session:
        async with session.get("https://trovesaurus.com/modsapi.php?mode=list&ml=whatevertheappis") as response:
            data = await response.json()
            if not hasattr(current_app, "mods_list"):
                current_app.mods_list = ModCache()
            cache = ModCache()
            for i, mod in enumerate(data, 1):
                ts_mod = TrovesaurusMod(**mod)
                cache[mod["id"]] = ts_mod
                for file in cache[mod["id"]].files:
                    if not file.hash:
                        continue
                    ts_entry = await ModEntry.find_one({"hash": file.hash})
                    if not ts_entry:
                        ts_entry = ModEntry(
                            hash=file.hash,
                            name=ts_mod.name,
                            format=file.format,
                            description=ts_mod.description,
                            author=ts_mod.author,
                        )
                    await ts_entry.save()
                    path = Path(f"mods/{file.hash}.{file.format}")
                    if not path.exists():
                        req = f"https://trovesaurus.com/client/downloadfile.php?fileid={file.id}"
                        async with session.get(req) as file_response:
                            file_data = await file_response.read()
                            with open(f"mods/{file.hash}.{file.format}", "wb") as f:
                                f.write(file_data)
                    else:
                        ...
            cache.process_hashes()
            current_app.mods_list = cache
    print("Mods list updated.")

