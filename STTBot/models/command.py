# External
import re


user_at_pattern = re.compile("<@.+>")


class Command:
    def __init__(self, raw_cmd, cmd, sub_cmd, args, default_sub_cmd=None):
        self.raw_cmd = raw_cmd
        self.cmd = cmd
        self.sub_cmd = sub_cmd
        self.args = args

    @classmethod
    def from_text(cls, text):
        cmd, sub_cmd, args = None, None, []

        words = text.split()
        if user_at_pattern.match(words[0]):
            words = words[1:]
        else:
            raise ValueError("Bot must be mentioned at start of message")

        if len(words) == 0:
            raise ValueError("Bot requires a command after mention")

        cmd = words[0].lower()
        if len(words) > 1:
            sub_cmd = words[1].lower()
        if len(words) > 2:
            args = words[2:]

        self = Command(raw_cmd=" ".join(words), cmd=cmd, sub_cmd=sub_cmd, args=args)
        return self
