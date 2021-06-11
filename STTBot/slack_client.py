# External
from slack import WebClient

# Internal
from STTBot import data_interface
from STTBot.utils import env


slack_oauth_token = env.get_cfg("SLACK_OAUTH_TOKEN")
testing_client = WebClient(slack_oauth_token)

clients = {
    "T019Q7SMYCW": testing_client
}


def get_client(team_id):
    return clients[team_id]


def set_client(team_id, token):
    clients[team_id] = WebClient(token)


def load_clients():
    tokens = data_interface.get_all_tokens()

    for team_id, token in tokens.items():
        set_client(team_id, token)
