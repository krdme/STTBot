# External
from flask import Flask
from gevent.pywsgi import WSGIServer

# Internal
from STTBot import slack_client
from STTBot.blueprints import admin, slack_events
from STTBot.utils import env


server_port = env.get_cfg("SERVER_PORT")
server_host = env.get_cfg("SERVER_HOST")
app = Flask(__name__)

with app.app_context():
    app.register_blueprint(admin.bot_admin_blueprint)
    app.register_blueprint(slack_events.bot_slack_events_blueprint)
    slack_client.load_clients()

http_server = WSGIServer((server_host, server_port), app, log=env.log)

try:
    http_server.serve_forever()
except KeyboardInterrupt:
    http_server.close()
    env.log.info("Shutting down")
