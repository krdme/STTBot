# Internal
from STTBot.utils import startup

args = vars(startup.parse_args())
log = startup.setup_logging(debug=args["debug"])
cfg = startup.load_config(args["env"])


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
