# External
from copy import deepcopy
import json
import traceback

# Internal
from slack_sdk import WebClient
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

    # Check whether sub_cmd could be an argument.
    if len(matching_cmd) == 0:
        matching_cmd = [command for command in commands if command['cmd'] == cmd and len(command['args']) > 0]
        if len(matching_cmd) != 0:
            command.args.insert(0, sub_cmd)

    if len(matching_cmd) == 0:
        return _ret_error(f"Unknown command `{command.raw_cmd}`", say)

    try:
        status = matching_cmd[0]['func'](client, event_data, command, say)
        suc_message = f"Successfully processed command `{command.raw_cmd}` in {channel}"
        if "message" in status.keys():
            _ret_success(status["message"], suc_message, say)
        elif "blocks" in status.keys():
            _ret_success_blocks(status["blocks"], suc_message, say)
    except Exception as e:
        return _ret_error(e, say)


def _cmd_help(client, event_data, command, say):
    cmds = "\n".join([
                         f"`{cmd['cmd']}{' ' + cmd['sub_cmd'] if cmd['sub_cmd'] is not None else ''}{''.join([' <' + arg + '>' for arg in cmd['args']])}` - {cmd['help']}"
                         for cmd in commands])
    message = f"Here is everything I can do:\n{cmds}"
    return {"message": message}


def _cmd_poll_react(client: WebClient, event_data, command, say):
    env.log.info(event_data)
    channel = event_data["event"].get("channel")
    timestamp = event_data["event"].get("ts")
    client.reactions_add(channel=channel, timestamp=timestamp, name="one")
    client.reactions_add(channel=channel, timestamp=timestamp, name="two")
    client.reactions_add(channel=channel, timestamp=timestamp, name="wastebasket")
    client.reactions_add(channel=channel, timestamp=timestamp, name="put_litter_in_its_place")
    return {}


def _cmd_pin(client, event_data, command, say):
    channel = event_data["event"].get("channel")
    message = data_interface.get_random_pin(channel=channel)

    if message is None:
        raise CommandError("No pins found")

    permalink_msg = message[3]
    return {"message": permalink_msg}


def _cmd_pin_any(client, event_data, command, say):
    message = data_interface.get_random_pin()

    if message is None:
        raise CommandError("No pins found")

    permalink_msg = message[3]
    return {"message": permalink_msg}


def _cmd_pin_channel(client, event_data, command, say):
    # Get channel-id from argument in '<#channel-id|channel-name>' format.
    channel_id = command.args[0].split('|')[0][2:]
    message = data_interface.get_random_pin(channel=channel_id)

    if message is None:
        channels = client.conversations_list()["channels"]
        matching_channel = [channel for channel in channels if channel["id"] == channel_id]
        if len(matching_channel) == 0:
            raise CommandError(f"Channel `{command.args[0]}` not found")
        else:
            raise CommandError("No pins found")

    permalink_msg = message[3]
    return {"message": permalink_msg}


def _cmd_pin_stats(client: WebClient, event_data, command, say):
    pins = data_interface.get_all_pins()
    channels = client.conversations_list(types="public_channel,private_channel")
    env.log.info(channels)
    users = client.users_list()
    pin_store = {}

    for pin in pins:
        this_channel = pin[0]
        message = pin[2]
        permalink = pin[3]
        pin_store[permalink] = {}

        if len(message.keys()) == 0:
            continue

        env.log.info(f"{this_channel} {message}")
        channel_name = [channel['name'] for channel in channels['channels'] if channel['id'] == this_channel][0]
        user = [user for user in users['members'] if user['id'] == message['user']][0]

        try:
            reactions = client.reactions_get(channel=this_channel, timestamp=message['ts'])
            env.log.info(f"Grabbed reactions for {channel_name} {message['ts']} at {permalink}")
        except SlackApiError:
            env.log.error(f"Couldn't grab {channel_name} {message['ts']} at {permalink}")
            continue

        pin_store[permalink]['channel'] = channel_name
        pin_store[permalink]['avatar'] = user['profile']['image_192']
        pin_store[permalink]['user'] = user['name']
        pin_store[permalink]['message'] = message['text']

        try:
            reaction_info = reactions['message']['reactions']
            reaction_count = 0
            for reaction in reaction_info:
                reaction_count += int(reaction['count'])
            pin_store[permalink]['reaction_count'] = reaction_count
            pin_store[permalink]['reactions'] = reaction_info
        except KeyError:
            pin_store[permalink]['reaction_count'] = 0
            pin_store[permalink]['reactions'] = {}

    user_count = {}
    for permalink, details in pin_store.items():
        user_count.setdefault(details['user'], {'count': 0, 'avatar': details['avatar']})
        user_count[details['user']]['count'] += 1

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Top Users:*"
            }
        },
        {
            "type": "divider"
        }
    ]
    block = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": ""
        },
        "accessory": {
            "type": "image",
            "image_url": "",
            "alt_text": "Avatar"
        }
    }

    for user, count_data in sorted(user_count.items(), key=lambda user: user[1]['count'], reverse=True)[:3]:
        my_block = deepcopy(block)
        my_block['text']['text'] = f"{user}\n{count_data['count']} pins"
        my_block['accessory']['image_url'] = count_data['avatar']
        blocks.append(my_block)

    blocks.extend([
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Top Reactions:*"
            }
        }
    ])

    for permalink, data in sorted(pin_store.items(), key=lambda dt: dt[1]['reaction_count'], reverse=True)[:3]:
        my_block = deepcopy(block)
        my_block['text']['text'] = f"{data['user']}\n{data['reaction_count']} reactions\n{data['message']}"
        my_block['accessory']['image_url'] = data['avatar']
        blocks.append(my_block)

    return {"blocks": blocks}


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
        pin_msg_details = client.conversations_history(earliest=permalink.timestamp, latest=permalink.timestamp,
                                                       limit=1, channel=permalink.channel, inclusive=True)
    except SlackApiError:
        env.log.warning("Could not find a message matching this permalink, adding with empty json")

    if len(pin_msg_details['messages']) == 0:
        env.log.warning("Could not find a message matching this permalink, adding with empty json")
    else:
        message_json = json.dumps(pin_msg_details['messages'][0])

    data_interface.insert_pin(event_data["event"].get("user"), permalink.channel, permalink.timestamp, message_json,
                              command.args[0])
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

    return {"message": f":white_check_mark: Successfully loaded {added_count} pins and ignored {ignored_count} pins"}


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


def _ret_success_blocks(blocks, suc_message, say):
    say(blocks=blocks)
    env.log.info(suc_message)
    return {"message": suc_message}, 200


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
        "help": "Prints a random pin from this channel",
        "func": _cmd_pin
    },
    {
        "cmd": "pin",
        "sub_cmd": "any",
        "args": [],
        "help": "Prints a random pin from any channel",
        "func": _cmd_pin_any
    },
    {
        "cmd": "pin",
        "sub_cmd": None,
        "args": [
            "channel"
        ],
        "help": "Prints a random pin from the specified channel",
        "func": _cmd_pin_channel
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
    },
    {
        "cmd": "pin",
        "sub_cmd": "stats",
        "args": [],
        "help": "Gets some stats on pinned messages",
        "func": _cmd_pin_stats
    },
    {
        "cmd": "poll",
        "sub_cmd": "react",
        "args": [],
        "help": "Adds reactions for pin showdown",
        "func": _cmd_poll_react
    },
]


class CommandError(Exception):
    """Used to represent any error received from API-Football."""
    pass
