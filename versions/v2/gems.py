# import ordered dict
import json
import re
from collections import OrderedDict
from copy import deepcopy

import easyocr
from quart import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from .models.builds import GemBuild
from .models.gems import *

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
    return jsonify(
        {
            gem_restriction.display_name: gem_restriction.value
            for gem_restriction in restrictions
        }
    )


@gems.route("/stat_types", methods=["GET"])
async def get_gem_stat_types():
    stat_types = sorted(list(GemStatType), key=lambda x: x.value)
    return jsonify(
        {
            gem_stat_type.display_name: gem_stat_type.value
            for gem_stat_type in stat_types
        }
    )


@gems.route("/augment_types", methods=["GET"])
async def get_gem_augment_types():
    augment_types = sorted(list(AugmentType), key=lambda x: x.value)
    return jsonify(
        {
            gem_augment_type.display_name: gem_augment_type.value
            for gem_augment_type in augment_types
        }
    )


@gems.route("/gem_abilities", methods=["GET"])
async def get_gem_abilities():
    abilities = sorted(list(GemAbility), key=lambda x: x.value)
    return jsonify(
        {gem_ability.display_name: gem_ability.value for gem_ability in abilities}
    )


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


@gems.route("/evaluate", methods=["POST"])
async def evaluate_gem():
    return "Hello from gem evaluation"
    level = re.compile(r"(?:Level|Nivel) (\d{1,2})", re.IGNORECASE)
    power_rank = re.compile(r"(?:Power Rank|Ranque de Poder) (\d{1,4})", re.IGNORECASE)
    # Stat capture
    magic_damage = re.compile(
        r"(?:Magic Damage) *((?:\d{1,3})(?:,\d{1,3})?(?:,\d{1,3})?)", re.IGNORECASE
    )
    physical_damage = re.compile(
        r"(?:Physical Damage) *((?:\d{1,3})(?:,\d{1,3})?(?:,\d{1,3})?)", re.IGNORECASE
    )
    critical_damage = re.compile(
        r"(?:Critical Damage) *((?:\d{1,3})(?:.\d{1,3})?)%", re.IGNORECASE
    )
    critical_hit = re.compile(
        r"(?:Critical Hit) ((?:\d{1,3})(?:.\d{1,3})?)%", re.IGNORECASE
    )
    maximum_health = re.compile(
        r"(?:Maximum Health) *((?:\d{1,3})(?:,\d{1,3})?(?:,\d{1,3})?)", re.IGNORECASE
    )
    maximum_health_bonus = re.compile(
        r"(?:Maximum Health) *((?:\d{1,3})(?:,\d{1,3})?(?:.\d{1,3})?)%", re.IGNORECASE
    )
    light = re.compile(
        r"(?:Light) *((?:\d{1,3})(?:,\d{1,3})?(?:,\d{1,3})?)", re.IGNORECASE
    )
    if request.method == "POST":
        # Get image file from "gem"
        image = (await request.files).get("gem")
        if not image:
            return abort(400, description="No gem file provided")

        reader = easyocr.Reader(
            [
                "en",
                "de",
                "fr",
                "pt",
            ],
            gpu=False,
        )

        result = reader.readtext(
            image.read(),
            detail=0,
            paragraph=True,
        )
        print(result)
        matched = {
            "level": None,
            "power_rank": None,
            "magic_damage": None,
            "physical_damage": None,
            "critical_damage": None,
            "critical_hit": None,
            "maximum_health": None,
            "maximum_health_bonus": None,
            "light": None,
        }
        for i in result:
            level_match = level.search(i)
            power_rank_match = power_rank.search(i)
            magic_damage_match = magic_damage.search(i)
            physical_damage_match = physical_damage.search(i)
            critical_damage_match = critical_damage.search(i)
            critical_hit_match = critical_hit.search(i)
            maximum_health_match = maximum_health.search(i)
            maximum_health_bonus_match = maximum_health_bonus.search(i)
            light_match = light.search(i)
            if level_match:
                matched["level"] = int(level_match.group(1))
            if power_rank_match:
                matched["power_rank"] = int(power_rank_match.group(1).replace(",", ""))
            if magic_damage_match:
                matched["magic_damage"] = int(
                    magic_damage_match.group(1).replace(",", "")
                )
            if physical_damage_match:
                matched["physical_damage"] = int(
                    physical_damage_match.group(1).replace(",", "")
                )
            if critical_damage_match:
                matched["critical_damage"] = float(
                    critical_damage_match.group(1).replace(",", "")
                )
            if critical_hit_match:
                matched["critical_hit"] = float(
                    critical_hit_match.group(1).replace(",", "")
                )
            if maximum_health_match:
                matched["maximum_health"] = int(
                    maximum_health_match.group(1).replace(",", "")
                )
            if maximum_health_bonus_match:
                matched["maximum_health_bonus"] = float(
                    maximum_health_bonus_match.group(1).replace(",", "")
                )
            if light_match:
                matched["light"] = int(light_match.group(1).replace(",", ""))
        for key, value in deepcopy(matched).items():
            if value is None:
                del matched[key]
        return jsonify({"message": json.dumps(matched, indent=4)})
