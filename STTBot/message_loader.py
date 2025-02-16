# External
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from slack_sdk.errors import SlackApiError

# Internal
import STTBot.data_interface as data_interface
from STTBot.utils import env


required_fields = ["ts", "user", "text"]
scheduler = BackgroundScheduler()


def get_messages(client):
    midnight = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_time = midnight - timedelta(days=2)
    end_time = midnight - timedelta(days=1)
    env.log.info(f"Refreshing messages between {start_time} and {end_time}")
    channel_response = client.conversations_list(types='public_channel,private_channel')
    channels = {channel['id']: channel['name'] for channel in channel_response['channels']}
    users_response = client.users_list()
    users = {user['id']: user['name'] for user in users_response['members']}

    for channel_id, channel_name in channels.items():
        oldest = f"{start_time.timestamp()}00000"
        latest = f"{end_time.timestamp()}00000"
        env.log.info(f"Start {oldest}, end {latest}")
        message_count = 0
        cursor = None
        has_more = True

        while has_more:
            try:
                message_response = client.conversations_history(channel=channel_id, cursor=cursor, oldest=oldest, latest=latest, inclusive=True)
            except SlackApiError as e:
                env.log.error(f"Could not get messages: {e.response}")
                break

            has_more = message_response.get('has_more', False)
            cursor = message_response.get('response_metadata', {'next_cursor': None}).get('next_cursor')
            messages = process_message_response(message_response, channel_id, channel_name, users)
            data_interface.insert_messages(messages)
            message_count += len(messages)

        env.log.info(f"Processed {message_count} messages for {channel_name}")
    env.log.info(f"Refresh complete. Next scheduled refresh is at {scheduler.get_job('refresh_messages').next_run_time.isoformat()}")


def process_message_response(message_response, channel_id, channel_name, users):
    messages = []
    for message in message_response.get('messages', []):
        message = resolve_missing_keys(message)
        if message is not None:
            permalink = f"{env.get_cfg('PERMALINK_BASE_URL')}/{channel_id}/p{message['ts'].replace('.', '')}"
            message = {'timestamp': message['ts'], 'channel_id': channel_id, 'channel_name': channel_name,
                       'user_id': message['user'], 'user_name': users[message['user']],
                       'message': message['text'], 'permalink': permalink}
            messages.append(message)

    return messages


def resolve_missing_keys(message):
    missing_keys = [key for key in required_fields if key not in message.keys()]

    if len(missing_keys) > 0:
        env.log.debug(f"Message with timestamp {message['ts']} missing required fields: {','.join(missing_keys)}")
        return None

    if 'user_profile' not in message.keys():
        message['user_profile'] = {'name': 'Unknown'}

    return message


def schedule_refresh(client):
    midnight = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    scheduler.add_job(
        func=get_messages,
        args=[client],
        trigger='interval',
        days=1,
        next_run_time=midnight,
        id='refresh_messages'
    )
    scheduler.start()
    return scheduler
