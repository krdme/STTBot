# External
from flask import Flask, request
from gevent.pywsgi import WSGIServer
from slack_bolt import App
from slack_bolt.oauth import OAuthFlow
from slack_bolt.adapter.flask import SlackRequestHandler

# Internal
from STTBot.events import app_mention
from STTBot.message_loader import schedule_refresh
from STTBot.utils import env


# - Startup procedure - #

env.init_env_vars()
flask_app = Flask(__name__)
bolt_app = App(oauth_flow=OAuthFlow.sqlite3(database=env.get_cfg("PATH_DB")))
handler = SlackRequestHandler(bolt_app)


def start():
    server_host = env.get_cfg("SERVER_HOST")
    server_port = env.get_cfg("SERVER_PORT")
    set_bot_token()
    scheduler = schedule_refresh(bolt_app.client)
    http_server = WSGIServer((server_host, server_port), flask_app, log=env.log)

    try:
        env.log.info("Started up")
        http_server.serve_forever()
    except KeyboardInterrupt:
        env.log.info("Shutting down")
        http_server.close()
        scheduler.shutdown()
        env.log.info("Shut down")


def set_bot_token():
    installation = bolt_app.installation_store.find_installation(team_id=env.get_cfg("AUTH_TEAM_ID"), enterprise_id=None)
    if installation is None:
        env.log.error("Can't find matching installation, either AUTH_TEAM_ID is not set or the bot isn't installed")
    else:
        bolt_app.client.token = installation.bot_token


# - Slack routes - #

@flask_app.route("/slack/install", methods=["GET"])
def route_slack_install():
    return handler.handle(request)


@flask_app.route("/slack/oauth_redirect", methods=["GET"])
def route_slack_oauth_redirect():
    return handler.handle(request)


@flask_app.route("/slack/events", methods=["POST"])
def route_slack_events():
    return handler.handle(request)


# - Slack handlers - #

@bolt_app.event("app_mention")
def handle_app_mention(client, body, say):
    app_mention.handle(client, body, say)


# - Custom routes - #

@flask_app.route("/status", methods=["GET"])
def route_status():
    return {"status": 200, "message": "All good!"}


if __name__ == "__main__":
    start()
