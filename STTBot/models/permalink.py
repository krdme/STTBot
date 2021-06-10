# Internal
from STTBot.utils import env

# External
import re

permalink_regex = "<?https:\\/\\/(.+).slack.com\\/archives\\/(.+?)\/p(\\d{16})>?"
permalink_regex = re.compile(permalink_regex)


class Permalink:
    def __init__(self, raw_permalink, server, channel, timestamp):
        self.raw_permalink = raw_permalink
        self.server = server
        self.channel = channel
        self.timestamp = timestamp

    @classmethod
    def from_text(cls, text):
        if re.match(permalink_regex, text):
            server, channel, timestamp = re.findall(permalink_regex, text)[0]
            timestamp = f"{timestamp[:-6]}.{timestamp[-5:]}"
            return Permalink(text, server, channel, timestamp)
        else:
            return None
