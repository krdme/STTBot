# External
from flask import Blueprint

# Internal
from STTBot.utils import env


bot_admin_route = env.get_cfg("BOT_ADMIN_ROUTE")
bot_admin_blueprint = Blueprint("bot_admin", __name__)


@bot_admin_blueprint.route(bot_admin_route + "/status")
def handle_status():
    return {"status": 200, "message": "All good!"}
