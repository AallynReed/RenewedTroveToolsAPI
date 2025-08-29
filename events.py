from __future__ import annotations

import websockets
import asyncio
from utils import Redis
import json


async def main():
    redis = Redis()
    async def generate(websocket, path):
        async for event in redis.event_listen():
            event = {
                "id": event.id,
                "event": event.type.name,
                "data": json.loads(event.json)
            }
            await websocket.send(json.dumps(event))
    await websockets.serve(generate, "localhost", 13011)
    await asyncio.get_running_loop().create_future()


loop = asyncio.new_event_loop()

loop.run_until_complete(main())