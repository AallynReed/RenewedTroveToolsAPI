from quart import make_response, render_template, jsonify
import re

def render_json(data):
    response = jsonify(data)
    return response

async def render(*args, **kwargs):
    template = await render_template(*args, **kwargs)
    response = await make_response(template)
    return response
    