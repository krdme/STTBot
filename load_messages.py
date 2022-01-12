# External
import os
import json
from apscheduler.schedulers.background import BackgroundScheduler

# Internal
from STTBot import data_interface
from STTBot.utils import env

# Global variables
db = env.get_cfg("PATH_DB")
data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
required_fields = ["ts", "user", "text"]
inserted_message_counts = {}

# Global accessors
scheduler = BackgroundScheduler()


def main():
    channel_dirs = [d.name for d in os.scandir(data_path) if d.is_dir()]
    channel_info = get_json_from_file(os.path.join(data_path, "channels.json"))

    for channel_dir in [os.path.join(data_path, channel_dir) for channel_dir in channel_dirs]:
        channel_name = os.path.basename(channel_dir)
        channel_id = [channel['id'] for channel in channel_info if channel['name'] == channel_name][0]
        env.log.info(f"Getting messages for {channel_name}")

        for message_file in os.scandir(channel_dir):
            message_data = process_message_file(message_file, channel_id)
            for message in message_data:
                message['channel_id'] = channel_id
                message['channel_name'] = channel_name
            data_interface.insert_messages(message_data)
            inserted_message_counts[channel_name] = inserted_message_counts.get(channel_name, 0) + len(message_data)

        env.log.info(f"Inserted/updated {inserted_message_counts[channel_name]} messages for {channel_name}")


def process_message_file(filepath, channel_id):
    message_file_json = get_json_from_file(filepath)

    message_data = []
    for message in message_file_json:
        message = resolve_missing_keys(message)
        if message is None:
            continue

        permalink = f"{env.get_cfg('PERMALINK_BASE_URL')}/{channel_id}/p{message['ts'].replace('.', '')}"
        message = {'timestamp': message['ts'], 'user_id': message['user'], 'user_name': message['user_profile']['name'], 'message': message['text'], 'permalink': permalink}
        message_data.append(message)

    return message_data


def resolve_missing_keys(message):
    missing_keys = [key for key in required_fields if key not in message.keys()]

    if len(missing_keys) > 0:
        env.log.debug(f"Message with timestamp {message['ts']} missing required fields: {','.join(missing_keys)}")
        return None

    if 'user_profile' not in message.keys():
        message['user_profile'] = {'name': 'Unknown'}

    return message


def get_json_from_file(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)


def log_inserted_counts():
    env.log.info(f"Current message counts: {', '.join([f'{k}:{v}' for k,v in inserted_message_counts.items()])}")


if __name__ == "__main__":
    scheduler.add_job(log_inserted_counts, trigger='interval', minutes=1)
    scheduler.start()
    main()
    scheduler.shutdown()
