# External
import argparse
import json
import logging


def parse_args():
    """Parses the command line arguments.
    Returns:
        Namespace: The parsed command line arguments.
    """

    parser = argparse.ArgumentParser(description="Slack bot for various STT functions")
    parser.add_argument("--debug", action="store_true", help="Show debug-level logging")
    parser.add_argument("--env", default=".env.prod.json", help="Path to the config file to use")
    return parser.parse_args()


def setup_logging(debug=False):
    """Set up logging format and level.
    Returns:
        Logger: The logger object to use throughout the script.
    """

    flask_log = logging.getLogger('werkzeug')
    flask_log.disabled = True
    log = logging.getLogger("STTBot")
    ch = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s — %(funcName)-20.20s — %(levelname)-4.4s — %(message)s")
    ch.setFormatter(formatter)
    log.addHandler(ch)
    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    return log


def load_config(path):
    """Loads a config file from the given path.
    Args:
        path (str): The filepath.
    Returns:
        dict: JSON data from the file.
    """

    try:
        with open(path, "r") as f:
            return json.load(f)
    except AttributeError:
        raise AttributeError("Unknown argument")
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file {path} wasn't found")
