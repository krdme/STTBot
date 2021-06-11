# External
from flask import Blueprint, request
from slack import WebClient

# Internal
from STTBot import data_interface, slack_client
from STTBot.utils import env


bot_admin_route = env.get_cfg("BOT_ADMIN_ROUTE")
bot_admin_blueprint = Blueprint("bot_admin", __name__)
client_id = env.get_cfg("SLACK_CLIENT_ID")
client_secret = env.get_cfg("SLACK_CLIENT_SECRET")
signing_secret = env.get_cfg("SLACK_SIGNING_SECRET")


@bot_admin_blueprint.route(bot_admin_route + "/status")
def handle_status():
    return {"status": 200, "message": "All good!"}


@bot_admin_blueprint.route(bot_admin_route + "/auth", methods=["GET", "POST"])
def handle_auth():
    auth_code = request.args["code"]
    client = WebClient()

    # Exchange the authorization code for an access token with Slack
    response = client.oauth_v2_access(
        client_id=client_id,
        client_secret=client_secret,
        code=auth_code
    )

    # Save the bot token and teamID to a database
    # In our example, we are saving it to dictionary to represent a DB
    team_id = response["team"]["id"]
    token = response["access_token"]
    data_interface.insert_token(team_id, token)
    slack_client.set_client(team_id, token)

    # Don't forget to let the user know that auth has succeeded!
    return {"status": 200, "message": "Auth complete!"}
