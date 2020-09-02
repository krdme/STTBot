# External
from flask import Flask

# Internal
from STTBot.blueprints import admin, slack_events
from STTBot.utils import env


server_port = env.get_cfg("SERVER_PORT")
app = Flask(__name__)

with app.app_context():
    app.register_blueprint(admin.bot_admin_blueprint)
    app.register_blueprint(slack_events.bot_slack_events_blueprint)

app.run(port=server_port)
