from quart import current_app
from ..utils import tasks
from aiohttp import ClientSession
from ..utils.trovesaurus import TrovesaurusMod
from ..utils.cache import ModCache


@tasks.loop(minutes=30)
async def update_mods_list():
    async with ClientSession() as session:
        async with session.get("https://trovesaurus.com/modsapi.php?mode=list&ml=whatevertheappis") as response:
            data = await response.json()
            if not hasattr(current_app, "mods_list"):
                current_app.mods_list = ModCache()
            cache = ModCache()
            for mod in data:
                cache[mod["id"]] = TrovesaurusMod(**mod)
            cache.process_hashes()
            current_app.mods_list = cache

