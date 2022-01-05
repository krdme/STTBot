# External
import json
import traceback
import random

# Internal
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

import STTBot.data_interface as data_interface
from STTBot.models.command import Command
from STTBot.models.permalink import Permalink
from STTBot.utils import env


def handle(client, event_data, say):
    if event_data["event"].get("subtype") != "bot_message":
        return _handle_user_mention(client, event_data, say)


def _handle_user_mention(client, event_data, say):
    text = event_data["event"].get("text")
    channel = event_data["event"].get("channel")
    command = Command.from_text(text)
    cmd = command.cmd
    sub_cmd = command.sub_cmd
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
        for cmd in sorted(commands, key=lambda k: (k['cmd'], k['sub_cmd'] if k['sub_cmd'] is not None else '_'))])
    message = f"Here is everything I can do:\n{cmds}"
    return {"message": message}


# - Pin commands - #


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


def _cmd_pin_leaderboard(client: WebClient, event_data, command, say):
    users = client.users_list()
    if len(command.args) == 1 and command.args[0] == "all":
        pins = data_interface.get_all_pins()
    else:
        channel = event_data["event"].get("channel")
        pins = data_interface.get_all_pins(channel=channel)

    if pins is None:
        raise CommandError("No pinned items in this channel")

    blocks = []
    blocks.extend(_build_top_users_block(users, pins, max_entries=5))

    return {"blocks": blocks}


# - Other commands - #


def _cmd_stt_draft(client, event_data, command, say):
    if len(command.args) == 0:
        raise CommandError("No list provided")
    else:
        draft_order = command.args
        random.shuffle(draft_order)
    ex = ' '    
    return {"message": f":robot_face: Order generated: {ex.join(draft_order)}"}


def _cmd_msg_leaderboard(client, event_data, command, say):
    if len(command.args) == 0:
        raise CommandError("Need a word to search")
    else:
        if command.args[0] == "raw":
            search_string = " ".join(command.args[1:])
            display_search_string = search_string
        else:
            search_string = f"\\b{' '.join(command.args).lower()}\\b"
            display_search_string = search_string[2:-2]

        leaderboard = data_interface.get_msg_leaderboard(search_string)
        if leaderboard is None:
            raise CommandError("No matches found")

        leader_str = '\n'.join([f'{k:14} {v}' for k, v in leaderboard.items()])
        message = f"""```user_name      Count of {display_search_string}\n{leader_str}```"""
        return {"message": message}


# - Helpers - #


def _get_top_users(users, pins):
    """Returns dict with the necessary data to create a top users leaderboard.

    Args:
        users: Return value of client.users_list().
        pins: The set of pins to be counted.

    Returns:
        A dict mapping usernames to a dict containing pin count and avatar URL. For example:
        {'user1': {'count': 3, 'avatar': <url.img>}, ...}
    """
    pin_store = {}
    for pin in pins:
        message = pin[2]
        permalink = pin[3]
        pin_store[permalink] = {}

        if len(message.keys()) == 0:
            continue

        try:
            user = [user for user in users['members'] if user['id'] == message['user']][0]
        except KeyError:
            env.log.error(f"Probably couldn't get userid for {message['ts']} at {permalink}")
            continue

        pin_store[permalink]['avatar'] = user['profile']['image_192']
        pin_store[permalink]['user'] = user['name']

    user_count = {}
    for permalink, details in pin_store.items():
        try:
            user_count.setdefault(details['user'], {'count': 0, 'avatar': details['avatar']})
            user_count[details['user']]['count'] += 1
        except KeyError:
            env.log.error(f"Failed to count {permalink} {details}")
    return user_count


def _build_block(avatar: str, name: str, text: str):
    """Returns a Slack block displaying avatar, name and text.

    Args:
        avatar: An image URL.
        name: The name to be displayed next to the avatar.
        text: Slack Markdown text displayed below the name. Use \n for newlines.
    """
    return {
        "type": "context",
        "elements": [
            {
                "type": "image",
                "image_url": avatar,
                "alt_text": "Avatar"
            },
            {
                "type": "mrkdwn",
                "text": f"*{name}*\n{text}"
            }
        ]
    }


def _build_stats_block(header, entries):
    """Returns a list of Slack blocks forming a leaderboard style display.

    Args:
        header (str): The header displayed above the leaderboard entries.
        entries: A list of dicts with keys: avatar (str), name (str) and text (str).
          The list is assumed to be sorted by order of placement: 1st, 2nd, 3rd, etc.
    """
    medals = {
        1: " :first_place_medal:",
        2: " :second_place_medal:",
        3: " :third_place_medal:"
    }
    stats_block = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{header}*"
            }
        }
    ]
    for i, item in enumerate(entries, start=1):
        stats_block.append(_build_block(item['avatar'], f"{item['name']}{medals.get(i, '')}", item['text']))

    return stats_block


def _build_top_users_block(users, pins, max_entries: int):
    """Returns a list of Slack blocks forming a top users leaderboard.

    Args:
        users: Return value of client.users_list().
        pins: The set of pins to be counted.
        max_entries: Maximum number of leaderboard entries to display.
    """
    user_count = _get_top_users(users, pins)
    entries = []
    for user, count_data in sorted(user_count.items(), key=lambda user: user[1]['count'], reverse=True)[:max_entries]:
        entries.append({
            'avatar': count_data['avatar'],
            'name': f"{user}",
            'text': f"{count_data['count']} pins"
        })
    return _build_stats_block("Top Users", entries)


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


# - Command map - #


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
        "sub_cmd": "leaderboard",
        "args": [
            "all"
        ],
        "help": "Gets top users from this channel by default, or all channels if `all` is provided as an argument",
        "func": _cmd_pin_leaderboard
    },
    {
        "cmd": "draft",
        "sub_cmd": None,
        "args": [
            "list_of_users"
        ],
        "help": "Randomises order of users for STT Draft",
        "func": _cmd_stt_draft
    },
    {
        "cmd": "msg",
        "sub_cmd": "leaderboard",
        "args": [
            "raw",
            "search_string"
        ],
        "help": "Returns the people who used the given search string the most",
        "func": _cmd_msg_leaderboard
    }
]


class CommandError(Exception):
    """Used to represent any error received from API-Football."""
    pass
