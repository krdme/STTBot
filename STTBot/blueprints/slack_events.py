# External
from flask import Blueprint
from slackeventsapi import SlackEventAdapter

# Internal
from STTBot.models.command import Command
from STTBot.slack_client import slack_client
from STTBot.utils import env


bot_slack_events_route = env.get_cfg("BOT_SLACK_EVENTS_ROUTE")
bot_user = env.get_cfg("BOT_USER_ID")
slack_signing_secret = env.get_cfg("SLACK_SIGNING_SECRET")
bot_slack_events_blueprint = Blueprint("bot_slack_events", __name__)
events_adapter = SlackEventAdapter(slack_signing_secret, bot_slack_events_route, bot_slack_events_blueprint)


@events_adapter.on("app_mention")
def handle_mention(event_data):
    env.log.info(event_data)
    message = event_data["event"]

    if message.get("user") == bot_user or message.get("subtype") == "bot_message":
        _handle_bot_mention(event_data)
    else:
        _handle_user_mention(event_data)


def _handle_bot_mention(event_data):
    env.log.info("Ignoring message from the bot")
    return


def _handle_user_mention(event_data):
    text = event_data["event"].get("text")
    command = Command.from_text(text)
    cmd = command.cmd
    sub_cmd = command.get_sub_cmd()

    if cmd == "fg":
        if sub_cmd == "round":
            _cmd_fg_round(event_data)
        if sub_cmd == "dab":
            _cmd_fg_dab(event_data)

    return {"status": 200}


def _cmd_fg_round(event_data):
    channel = event_data["event"].get("channel")
    message = "Did you make it through this round?"
    resp = slack_client.chat_postMessage(channel=channel, text=message)
    resp_ts = resp.get("ts")
    slack_client.reactions_add(name="heavy_check_mark", channel=channel, timestamp=resp_ts)
    slack_client.reactions_add(name="x", channel=channel, timestamp=resp_ts)


def _cmd_fg_dab(event_data):
    channel = event_data["event"].get("channel")
    message = ":fgdab:"
    slack_client.chat_postMessage(channel=channel, text=message)
