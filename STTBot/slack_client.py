from slack import WebClient

from STTBot.utils import env


slack_oauth_token = env.get_cfg("SLACK_OAUTH_TOKEN")
slack_client = WebClient(slack_oauth_token)
