from aiohttp import ClientSession


async def send_embed(webhook_url, embed):
    async with ClientSession() as session:
        await session.post(webhook_url, json={"embeds": [embed]})