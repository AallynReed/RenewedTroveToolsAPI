from quart import Blueprint, request, abort, jsonify, current_app, Response, send_file
from aiohttp import ClientSession
from os import getenv
import matplotlib.pyplot as plt
from io import BytesIO
import humanize

misc = Blueprint('misc', __name__, url_prefix='/misc')

def format_number(number):
    if number < 0:
        return "-" + format_number(abs(number))
    if number >= 1000000:
        return humanize.intword(number, format="%.2f").replace(" ", "").replace("million", "M")
    elif number >= 1000:
        return humanize.intword(number, format="%.2f").replace(" ", "").replace("thousand", "K")
    else:
        return str(number)

@misc.route('/feedback', methods=['POST'])
async def feedback():
    data = await request.json
    message = data.get("message")
    if not message:
        return abort(400, "Missing message field.")
    embed = {
        "description": message,
    }

    payload = {
        "embeds": [embed]
    }
    async with ClientSession() as session:
        async with session.post(getenv("FEEDBACK_WEBHOOK"), json=payload) as resp:
            return Response(status=resp.status)

@misc.route('/change_log')
async def change_log():
    if not hasattr(current_app, "github_change_log"):
        return abort(503, "Change log is not available.")
    return jsonify(current_app.github_change_log)

@misc.route('/twitch_streams')
async def streams():
    if not hasattr(current_app, "twitch_streams"):
        return abort(503, "Twitch streams are not available.")
    return jsonify(current_app.twitch_streams)

@misc.route('/opn_chart')
async def opn_chart():
    plt.clf()
    plt.style.use('dark_background')
    fig, ax1 = plt.subplots()
    params = request.args
    forge_frag = int(params["forge_frag"])
    nitro_price = int(params["nitro_price"])
    nitro_sell = bool(int(params.get("nitro_sell", 0)))
    nitro_value = 175
    profit_points = {}
    market_cap = {}
    min_fpn = -300
    max_fpn = 601
    for uber in range(8, 12):
        m = [0, 0, 0, 0]
        c = [0, 0, 0, 0]
        i = 0
        x = 1000
        x_axis = []
        y_axis = []
        for z in range(100):
            nitro = (nitro_value * (z + 1))
            i += x
            i += 1500 / (uber - 7) - forge_frag * (10 * (uber - 7) - 10)
            if nitro_sell:
                i += -nitro_value * nitro_price
            f_p_n = i / nitro
            if i < m[1]:
                m = [z+1, i, nitro, f_p_n]
            if f_p_n < nitro_price:
                c = [z+1, i, nitro, f_p_n]
            x_axis.append(f_p_n)
            y_axis.append(nitro)
            x += 2000
        profit_points[uber] = m
        market_cap[uber] = c
        ax1.plot(y_axis, x_axis, label=f"Uber {uber}")
    ax1.set_title("Chart for flux cost during refinements")
    ax1.axhline(y = 0, color = 'green', linestyle = 'dashed', label = "0 ea") 
    ax1.axhline(y = nitro_price, color = 'red', linestyle = 'dashed', label = f"{nitro_price} ea")
    ax2 = ax1.twiny()
    # ax3 = ax1.twinx()
    ax1.set_xticks(range(0, 17501, 1750))
    ax1.set_yticks(range(min_fpn, max_fpn, 100))
    ax2.set_xticks(range(-5, 106, 5))
    ax1.set_xlabel("Nitro obtained")
    ax1.set_ylabel("Flux per nitro (ea)")
    ax2.set_xlabel("Refinements done")
    # ax3.set_ylabel("Flux cost")
    ax2.grid(visible=True, axis="x", color="purple", linestyle='dashed')
    labels = ax2.get_xticklabels()
    labels[0] = labels[-1] = ""
    ax2.set_xticklabels(labels)
    # ax3labels = ax1.get_yticklabels()
    # ax3.set_yticks(range(0, 10))
    # for l in ax3labels:
    #     l.set_text(f"{int(l.get_text().replace('−', '-'))*17500:,}")
    # ax3.set_yticklabels(ax3labels)
    legend_1 = ax1.legend(loc=2, borderaxespad=1.)
    legend_1.remove()
    legend_2 = ax2.legend(loc=2, borderaxespad=1.)
    legend_2.remove()
    # ax3.legend(loc=1, borderaxespad=1.)
    ax2.add_artist(legend_1)
    # ax3.add_artist(legend_2)
    x_pf = [x[2] for x in profit_points.values()]
    y_pf = [x[3] for x in profit_points.values()]
    z_pf = [f"{x[0]} | {format_number(-x[1])}" for x in profit_points.values()]
    for i, txt in enumerate(z_pf):
        ax1.annotate(txt, (x_pf[i], y_pf[i]))
    x_mc = [x[2] for x in market_cap.values()]
    y_mc = [x[3] for x in market_cap.values()]
    z_mc = [f"{x[0]}\n{format_number(-x[1])}" for i, x in enumerate(market_cap.values())]
    for i, txt in enumerate(z_mc):
        ax1.annotate(txt, (x_mc[i], y_mc[i]))
    data = BytesIO()
    plt.savefig(data, format="png", bbox_inches='tight', dpi=300)
    data.seek(0)
    return await send_file(data, mimetype="image/png")
