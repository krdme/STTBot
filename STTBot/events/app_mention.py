# External
import json
import traceback

# Internal
from slack_sdk.errors import SlackApiError
from STTBot.models.command import Command
from STTBot.models.permalink import Permalink
from STTBot.utils import env
import STTBot.data_interface as data_interface


def handle(client, event_data, say):
    if event_data["event"].get("subtype") != "bot_message":
        return _handle_user_mention(client, event_data, say)


def _handle_user_mention(client, event_data, say):
    text = event_data["event"].get("text")
    channel = event_data["event"].get("channel")
    command = Command.from_text(text)
    cmd = command.cmd
    sub_cmd = command.get_sub_cmd()
    env.log.info(f"Received command `{command.raw_cmd}` in {channel}")

    matching_cmd = [command for command in commands if command['cmd'] == cmd and command['sub_cmd'] == sub_cmd]

    if len(matching_cmd) == 0:
        return _ret_error(f"Unknown command `{command.raw_cmd}`", say)

    try:
        status = matching_cmd[0]['func'](client, event_data, command, say)
        suc_message = f"Successfully processed command `{command.raw_cmd}` in {channel}"
        return _ret_success(status["message"], suc_message, say)
    except Exception as e:
        return _ret_error(e, say)


def _cmd_help(client, event_data, command, say):
    cmds = "\n".join([f"`{cmd['cmd']}{' ' + cmd['sub_cmd'] if cmd['sub_cmd'] is not None else ''}{''.join([' <' + arg + '>' for arg in cmd['args']])}` - {cmd['help']}" for cmd in commands])
    message = f"Here is everything I can do:\n{cmds}"
    return {"message": message}


def _cmd_pin(client, event_data, command, say):
    channel = event_data["event"].get("channel")
    message = data_interface.get_random_pin(channel=channel)

    if message is None:
        raise CommandError("No pins found")

    permalink_msg = message[3]
    return {"message": permalink_msg}


def _cmd_pin_add(client, event_data, command, say):
    if len(command.args) == 0:
        raise CommandError(f"Need a permalink to pin")

    message_json = "{}"
    permalink = Permalink.from_text(command.args[0])

    if permalink is None:
        raise CommandError(f"{command.args[0]} does not seem like a valid permalink")
    elif data_interface.get_pin(permalink.channel, permalink.timestamp) is not None:
        raise CommandError("Message is already pinned")

    try:
        pin_msg_details = client.conversations_history(earliest=permalink.timestamp, latest=permalink.timestamp, limit=1, channel=permalink.channel, inclusive=True)
    except SlackApiError:
        env.log.warning("Could not find a message matching this permalink, adding with empty json")

    if len(pin_msg_details['messages']) == 0:
        env.log.warning("Could not find a message matching this permalink, adding with empty json")
    else:
        message_json = json.dumps(pin_msg_details['messages'][0])

    data_interface.insert_pin(event_data["event"].get("user"), permalink.channel, permalink.timestamp, message_json, command.args[0])
    return {"message": ":white_check_mark: Successfully added pin", "added": True}


def _cmd_pin_load(client, event_data, command, say):
    msg_channel = event_data["event"].get("channel")
    pins = client.pins_list(channel=msg_channel)
    env.log.info(pins)
    added_count = 0
    ignored_count = 0

    for pin in pins['items']:
        raw_permalink = pin[pin['type']]['permalink']
        message_json = json.dumps(pin[pin['type']])
        env.log.info(f"pin add {raw_permalink}")

        if pin['type'] == "message":
            permalink = Permalink.from_text(raw_permalink)
            channel = permalink.channel
            timestamp = permalink.timestamp
        elif pin['type'] == "file":
            channel = pin['file']['pinned_to'][0]
            timestamp = pin['file']['timestamp']

        if data_interface.get_pin(permalink.channel, permalink.timestamp) is None:
            data_interface.insert_pin(event_data["event"].get("user"), channel, timestamp, message_json, raw_permalink)
            added_count += 1
        else:
            ignored_count += 1

    return {"message":  f":white_check_mark: Successfully loaded {added_count} pins and ignored {ignored_count} pins"}


def _cmd_pin_remove(client, event_data, command, say):
    if len(command.args) == 0:
        raise CommandError(f"Need a permalink to remove")

    permalink = Permalink.from_text(command.args[0])

    if permalink is None:
        raise CommandError("Message does not seem like a valid permalink")
    elif data_interface.get_pin(permalink.channel, permalink.timestamp) is None:
        raise CommandError("No matching pin found")

    data_interface.remove_pin(permalink.channel, permalink.timestamp)
    return {"message": ":white_check_mark: Successfully removed pin"}


def _ret_error(error, say):
    say(f":warning: {error}")
    env.log.warning(error)
    env.log.warning(traceback.print_exc())
    return {"error": error}, 400


def _ret_success(ret_message, suc_message, say):
    say(ret_message, unfurl_links=True, unfurl_media=True)
    env.log.info(suc_message)
    return {"message": ret_message}, 200


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


class CommandError(Exception):
    """Used to represent any error received from API-Football."""
    pass
