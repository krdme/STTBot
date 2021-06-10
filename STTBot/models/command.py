# Internal
from STTBot.utils import env

default_sub_cmds = {"fg": "round"}


class Command:
    def __init__(self, raw_cmd, cmd, sub_cmd, args, default_sub_cmd=None):
        self.raw_cmd = raw_cmd
        self.cmd = cmd
        self.sub_cmd = sub_cmd
        self.args = args
        self.default_sub_cmd = default_sub_cmd

    def get_sub_cmd(self):
        if self.sub_cmd is not None:
            return self.sub_cmd
        else:
            return self.default_sub_cmd

    @classmethod
    def from_text(cls, text):
        cmd, sub_cmd, args, default_sub_cmd = None, None, [], None

        words = text.split()
        if words[0] == f"<@{env.get_cfg('BOT_USER_ID')}>":
            words = words[1:]
        else:
            raise ValueError("Bot must be mentioned at start of message")

        if len(words) == 0:
            raise ValueError("Bot requires a command after mention")

        cmd = words[0]
        if len(words) > 1:
            sub_cmd = words[1]
        if len(words) > 2:
            args = words[2:]

        if cmd in default_sub_cmds.keys():
            default_sub_cmd = default_sub_cmds[cmd]

        self = Command(raw_cmd=" ".join(words), cmd=cmd, sub_cmd=sub_cmd, args=args, default_sub_cmd=default_sub_cmd)
        return self
