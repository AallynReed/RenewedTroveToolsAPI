from quart import Response, Blueprint, stream_with_context, current_app
import asyncio


api_events = Blueprint("events", __name__, url_prefix="/events")


async def generate():
    counter = 0
    while True:
        counter += 1
        await asyncio.sleep(2)
        yield f"data: Message {counter}\n\n"


@api_events.route("/test")
async def test_events():
    return Response(generate(), content_type="text/event-stream")


@api_events.route("/")
async def events():
    @stream_with_context
    async def feed():
        async for event in current_app.redis.event_listen():
            yield f"id: {event.id}\n"
            yield f"event: {event.type.name}\n"
            yield f"data: {event.json}\n\n"

    return Response(feed(), content_type="text/event-stream")
