from quart import make_response, render_template, jsonify
import redis.asyncio as aioredis
from json import loads, dumps
import pickle
from enum import Enum
from pydantic import BaseModel
import json
import asyncio


def render_json(data):
    response = jsonify(data)
    return response


async def render(*args, **kwargs):
    template = await render_template(*args, **kwargs)
    response = await make_response(template)
    return response


class EventType(Enum):
    heartbeat = "heartbeat"
    challenge = "challenge"
    chaoschest = "chaos_chest"
    luxion = "luxion"
    corruxion = "corruxion"
    fluxion = "fluxion"
    market = "market"
    leaderboards = "leaderboards"


class Event(BaseModel):
    id: int
    type: EventType
    data: dict

    @property
    def json(self):
        return json.dumps(self.data)


class Redis:
    def __init__(self):
        self.server = None
        asyncio.create_task(self.connect())

    async def connect(self):
        self.server = await aioredis.Redis(host="localhost", port=6379)
        self.set = self.server.set
        self.get = self.server.get
        self.delete = self.server.delete
        self.expire = self.server.expire
        self.scan_iter = self.server.scan_iter

    @property
    def is_connected(self):
        return self.server is not None

    async def publish(self, channel, message):
        await self.server.publish(channel, pickle.dumps(message))

    async def publish_event(self, event):
        await self.publish(event.type.value, event)

    async def event_listen(self):
        pubsub = self.server.pubsub()
        for channel in EventType:
            await pubsub.subscribe(channel.value)
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield pickle.loads(message["data"])

    async def get_value(self, key):
        value = await self.server.get(key)
        if value is None:
            return value
        return loads(value.decode("utf-8"))

    async def set_value(self, key, value):
        return await self.server.set(key, dumps(value))

    async def get_object(self, key):
        value = await self.server.get(key)
        if value is None:
            return value
        return pickle.loads(value)

    async def set_object(self, key, value):
        return await self.server.set(key, pickle.dumps(value))
