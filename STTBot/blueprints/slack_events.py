# External
from flask import Blueprint, Response
from slack.errors import SlackApiError
from slackeventsapi import SlackEventAdapter
import json

# Internal
from STTBot import slack_client
from STTBot.models.command import Command
from STTBot.models.permalink import Permalink
from STTBot.utils import env
import STTBot.data_interface as data_interface


bot_slack_events_route = env.get_cfg("BOT_SLACK_EVENTS_ROUTE")
slack_signing_secret = env.get_cfg("SLACK_SIGNING_SECRET")
bot_slack_events_blueprint = Blueprint("bot_slack_events", __name__)
events_adapter = SlackEventAdapter(slack_signing_secret, bot_slack_events_route, bot_slack_events_blueprint)
this_event_data = None
this_slack_client = None


@bot_slack_events_blueprint.app_errorhandler(500)
def handle_error(err):
    env.log.error(err)
    channel = this_event_data["event"].get("channel")
    this_slack_client.chat_postMessage(channel=channel, text=f":warning: Unexpected error, shout at Keith")
    resp = Response({"status": 500})
    resp.headers['X-Slack-No-Retry'] = 1
    resp.status_code = 500
    return resp


@events_adapter.on("app_mention")
def handle_mention(event_data):
    env.log.info(event_data)
    global this_event_data, this_slack_client
    message = event_data["event"]
    team_id = event_data["team_id"]
    this_event_data = event_data
    this_slack_client = slack_client.get_client(team_id)

    if message.get("subtype") == "bot_message":
        return _handle_bot_mention(event_data)
    else:
        return _handle_user_mention(event_data)


def _handle_bot_mention(event_data):
    env.log.info("Ignoring message from a bot")
    return {"status": 200}, 200


def _handle_user_mention(event_data):
    text = event_data["event"].get("text")
    channel = event_data["event"].get("channel")
    command = Command.from_text(text)
    cmd = command.cmd
    sub_cmd = command.get_sub_cmd()
    env.log.info(f"Received command `{command.raw_cmd}` in {channel}")

    matching_cmd = [command for command in commands if command['cmd'] == cmd and command['sub_cmd'] == sub_cmd]

    if len(matching_cmd) == 1:
        status = matching_cmd[0]['func'](event_data, command)
    else:
        return _throw_error(f"Unknown command `{command.raw_cmd}`", channel)

    if type(status) is Response:
        return status
    else:
        this_slack_client.chat_postMessage(channel=channel, text=status['message'])
        env.log.info(f"Completed processing `{command.raw_cmd}` in {channel}")
        resp = Response({"status": 200})
        resp.headers['X-Slack-No-Retry'] = 1
        resp.status_code = 200
        return resp


def _cmd_help(event_data, command):
    cmds = "\n".join([f"`{cmd['cmd']}{' ' + cmd['sub_cmd'] if cmd['sub_cmd'] is not None else ''}{''.join([' <' + arg + '>' for arg in cmd['args']])}` - {cmd['help']}" for cmd in commands])
    message = f"Here is everything I can do:\n{cmds}"
    return {"message": message}


def _cmd_pin(event_data, command):
    channel = event_data["event"].get("channel")
    message = data_interface.get_random_pin()

    if message is None:
        return _throw_error("No pins found", channel)

    permalink_msg = this_slack_client.chat_getPermalink(channel=message[0], message_ts=message[1])
    return {"message": permalink_msg['permalink']}


def _cmd_pin_add(event_data, command):
    channel = event_data["event"].get("channel")
    permalink = Permalink.from_text(command.args[0])

    if permalink is None:
        return _throw_error(f"{command.args[0]} does not seem like a valid permalink", channel)

    try:
        pin_msg_details = this_slack_client.conversations_history(earliest=permalink.timestamp, latest=permalink.timestamp, limit=1, channel=permalink.channel, inclusive=True)
    except SlackApiError as e:
        return _throw_error(f"Could not find a message matching that pin {e}", channel)

    if len(pin_msg_details['messages']) == 0:
        return _throw_error("Could not find a message matching that pin", channel)
    elif data_interface.get_pin(permalink.channel, permalink.timestamp) is not None:
        return _throw_error("Message is already pinned", channel)

    message_json = json.dumps(pin_msg_details['messages'][0])
    data_interface.insert_pin(event_data["event"].get("user"), permalink.channel, permalink.timestamp, message_json)
    return {"message": ":white_check_mark: Successfully added pin", "added": True}


def _cmd_pin_load(event_data, command):
    channel = event_data["event"].get("channel")
    pins = this_slack_client.pins_list(channel=channel)
    added_count = 0
    failed_count = 0

    for pin in pins['items']:
        permalink = pin['message']['permalink']
        command = Command(f"pin add {permalink}", "pin", "add", [permalink])
        status = _cmd_pin_add(event_data, command)

        if type(status) is Response:
            failed_count += 1
        if status['added']:
            added_count += 1

    return {"message":  f":white_check_mark: Successfully loaded {added_count} pins and ignored {failed_count} pins"}


def _cmd_pin_remove(event_data, command):
    channel = event_data["event"].get("channel")
    permalink = Permalink.from_text(command.args[0])

    if permalink is None:
        return _throw_error("Message does not seem like a valid permalink", channel)

    if data_interface.get_pin(permalink.channel, permalink.timestamp) is None:
        return _throw_error("No matching pin found", channel)

    data_interface.remove_pin(permalink.channel, permalink.timestamp)
    return {"message": ":white_check_mark: Successfully removed pin"}


def _throw_error(message, channel):
    env.log.warning(message)
    this_slack_client.chat_postMessage(channel=channel, text=f":warning: {message}")
    resp = Response({"status": 400})
    resp.headers['X-Slack-No-Retry'] = 1
    resp.status_code = 400
    return resp


commands = [
    {
        "cmd": "help",
        "sub_cmd": None,
        "args": [],
        "help": "Prints this message",
        "func": _cmd_help
    },
    {
        "cmd": "pin",
        "sub_cmd": None,
        "args": [],
        "help": "Prints a random pin",
        "func": _cmd_pin
    },
    {
        "cmd": "pin",
        "sub_cmd": "add",
        "args": [
            "message_permalink"
        ],
        "help": "Adds a message to the database",
        "func": _cmd_pin_add
    },
    {
        "cmd": "pin",
        "sub_cmd": "load",
        "args": [],
        "help": "Adds all current pins in this channel to the database",
        "func": _cmd_pin_load
    },
    {
        "cmd": "pin",
        "sub_cmd": "remove",
        "args": [
            "message_permalink"
        ],
        "help": "Removes a message from the database",
        "func": _cmd_pin_remove
    }
]
