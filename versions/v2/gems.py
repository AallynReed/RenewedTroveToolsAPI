from quart import Blueprint, request, abort, current_app, Response, jsonify, render_template, redirect, url_for
from .models.gems import *
from .models.builds import GemBuild
# import ordered dict
from collections import OrderedDict

gems = Blueprint("gems", __name__, url_prefix="/gems")

@gems.route("/types", methods=["GET"])
async def get_gem_types():
    types = sorted(list(GemType), key=lambda x: x.value)
    return jsonify({gem_type.display_name: gem_type.value for gem_type in types})

@gems.route("/elements", methods=["GET"])
async def get_gem_elements():
    elements = sorted(list(GemElement), key=lambda x: x.value)
    return jsonify({element.display_name: element.value for element in elements})

@gems.route("/tiers", methods=["GET"])
async def get_gem_tiers():
    tiers = sorted(list(GemTier), key=lambda x: x.value)
    return jsonify({gem_tier.display_name: gem_tier.value for gem_tier in tiers})

@gems.route("/restrictions", methods=["GET"])
async def get_gem_restrictions():
    restrictions = sorted(list(GemRestriction), key=lambda x: x.value)
    return jsonify({gem_restriction.display_name: gem_restriction.value for gem_restriction in restrictions})

@gems.route("/stat_types", methods=["GET"])
async def get_gem_stat_types():
    stat_types = sorted(list(GemStatType), key=lambda x: x.value)
    return jsonify({gem_stat_type.display_name: gem_stat_type.value for gem_stat_type in stat_types})

@gems.route("/augment_types", methods=["GET"])
async def get_gem_augment_types():
    augment_types = sorted(list(AugmentType), key=lambda x: x.value)
    return jsonify({gem_augment_type.display_name: gem_augment_type.value for gem_augment_type in augment_types})

@gems.route("/gem_abilities", methods=["GET"])
async def get_gem_abilities():
    abilities = sorted(list(GemAbility), key=lambda x: x.value)
    return jsonify({gem_ability.display_name: gem_ability.value for gem_ability in abilities})

@gems.route("/create", methods=["GET", "POST"])
async def create_gem():
    data = await request.get_json()
    if data is not None:
        gem = Gem.create(**data)
    else:
        gem = Gem.create()
    return jsonify(gem.model_dump())

@gems.route("/update", methods=["GET", "POST"])
async def update_gem():
    data = await request.get_json()
    gem_data = data.get("gem")
    if not gem_data:
        return abort(400, description="Missing required fields")
    gem = Gem(**gem_data)
    return jsonify(gem.model_dump())

@gems.route("/mass_update", methods=["GET", "POST"])
async def mass_update_gems():
    data = await request.get_json()
    gem_data = data.get("gems")
    if not gem_data:
        return abort(400, description="Missing required fields")
    print(gem_data)
    gems = []
    for gem in gem_data:
        if gem is None:
            gems.append(None)
        else:
            gems.append(Gem(**gem).model_dump())
    print(gems)
    return jsonify({"gems": gems})

@gems.route("/level_up", methods=["POST"])
async def level_up_gem():
    data = await request.get_json()
    gem_data = data.get("gem")
    if not gem_data:
        return abort(400, description="Missing required fields")
    gem = Gem(**gem_data)
    gem.level_up()
    return jsonify(gem.model_dump())

@gems.route("/augment", methods=["POST"])
async def augment_gem():
    data = await request.get_json()
    gem_data = data.get("gem")
    stat_data = data.get("stat")
    augment_data = data.get("augment")
    if not all([gem_data, stat_data, augment_data]):
        return abort(400, description="Missing required fields")
    gem = Gem(**gem_data)
    if not gem.has_stat(stat_data):
        return abort(400, description="Stat type not found in gem")
    for stat in gem.stats:
        if stat.type == GemStatType(stat_data):
            success = stat.add_augment(AugmentType(augment_data))
            if not success:
                abort(400, description="Stat is already fully augmented")
            return jsonify(gem.model_dump())

@gems.route("/spark", methods=["POST"])
async def reroll_gem_stat():
    data = await request.get_json()
    gem_data = data.get("gem")
    stat_data = data.get("stat")
    if not all([gem_data, stat_data]):
        return abort(400, description="Missing required fields")
    gem = Gem(**gem_data)
    if not gem.has_stat(stat_data):
        return abort(400, description="Stat type not found in gem")
    gem.reroll_stat_type(GemStatType(stat_data))
    return jsonify(gem.model_dump())

@gems.route("/flare", methods=["POST"])
async def flare_gem_stat():
    data = await request.get_json()
    gem_data = data.get("gem")
    stat_data = data.get("stat")
    if not all([gem_data, stat_data]):
        return abort(400, description="Missing required fields")
    gem = Gem(**gem_data)
    if not gem.has_stat(stat_data):
        return abort(400, description="Stat type not found in gem")
    gem.move_proc(GemStatType(stat_data))
    return jsonify(gem.model_dump())

###



###

@gems.route("/")
async def gem_page():
    return redirect(url_for("gem_page").replace("trove.", "app."))