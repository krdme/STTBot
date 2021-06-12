# External
import os

# Internal
from STTBot.utils import startup


args = vars(startup.parse_args())
log = startup.setup_logging(debug=args["debug"])
cfg = startup.load_config(args["env"])


def init_env_vars():
    os.environ["SLACK_SIGNING_SECRET"] = get_cfg("SLACK_SIGNING_SECRET")
    os.environ["SLACK_CLIENT_ID"] = get_cfg("SLACK_CLIENT_ID")
    os.environ["SLACK_CLIENT_SECRET"] = get_cfg("SLACK_CLIENT_SECRET")
    os.environ["SLACK_SCOPES"] = get_cfg("SLACK_SCOPES")


def get_cfg(key):
    """Gets a variable listed in the environment config file.
    Args:
        key (str): The key of the variable in the config file.
    Returns:
        The value of the given key in the config file.
    """

    return cfg.get(key)


def get_arg(arg):
    """Gets a command-line arguments value.
    Args:
        arg (str): The name of the command-line argument.
    Returns:
        The value of the command-line argument.
    """

    return args[arg]
