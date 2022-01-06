# External
import re
import sqlite3
import json
from collections import defaultdict

# Internal
from STTBot.utils import env


db = env.get_cfg("PATH_DB")


def get_cur():
    con = sqlite3.connect(db, isolation_level=None)
    con.set_trace_callback(env.log.info)
    con.create_function("REGEXP", 2, regexp)
    return con.cursor()


def regexp(expr, item):
    reg = re.compile(expr)
    return reg.search(item) is not None


# - Pin queries - #

def get_pin(channel, timestamp):
    cur = get_cur()
    cur.execute(Query.GET_PIN, (channel, timestamp))
    row = cur.fetchone()
    cur.close()

    if row is None:
        return None
    else:
        return row[0], row[1], json.loads(row[2]), row[3]


def get_random_pin(channel=None):
    cur = get_cur()
    if channel is not None:
        cur.execute(Query.GET_RANDOM_PIN_FROM_CHANNEL, [channel])
    else:
        cur.execute(Query.GET_RANDOM_PIN)
    row = cur.fetchone()
    cur.close()

    if row is None:
        return None
    else:
        return row[0], row[1], json.loads(row[2]), row[3]


def get_all_pins(channel=None):
    cur = get_cur()
    if channel is not None:
        cur.execute(Query.GET_ALL_PINS_FROM_CHANNEL, [channel])
    else:
        cur.execute(Query.GET_ALL_PINS)
    rows = cur.fetchall()
    cur.close()

    if len(rows) == 0:
        return None
    else:
        return [[row[0], row[1], json.loads(row[2]), row[3]] for row in rows]


def insert_pin(user, channel, timestamp, message_json, permalink):
    cur = get_cur()
    cur.execute(Query.INSERT_PIN, (user, channel, timestamp, message_json, permalink))
    cur.close()


def remove_pin(channel, timestamp):
    cur = get_cur()
    cur.execute(Query.REMOVE_PIN, (channel, timestamp))
    cur.close()


# - Other - #

def get_msg_leaderboard(search):
    cur = get_cur()
    cur.execute(Query.MSG_LEADERBOARD, [search])
    rows = cur.fetchall()
    cur.close()

    leaderboard = {}
    if len(rows) == 0:
        return None
    else:
        for row in rows:
            leaderboard[row[0]] = int(row[1])

    return leaderboard


def get_msg_match(search):
    cur = get_cur()
    cur.execute(Query.MSG_MATCH, [search])
    rows = cur.fetchall()
    cur.close()

    leaderboard = defaultdict(int)
    if len(rows) == 0:
        return None
    else:
        pattern = re.compile(search)
        for row in rows:
            matches = pattern.findall(row[0])
            for match in matches:
                leaderboard[match] += 1

    return_dict = {}
    num_to_display = 10
    for k, v in sorted(leaderboard.items(), key=lambda x: x[1], reverse=True):
        return_dict[k] = v
        num_to_display -= 1
        if num_to_display <= 0:
            break

    return return_dict


# - Constants - #


class Table:
    PINS = "pins"
    MESSAGES = "messages"


class Query:
    GET_ALL_PINS = f"SELECT channel, timestamp, json, permalink FROM {Table.PINS} ORDER BY created_at"
    GET_ALL_PINS_FROM_CHANNEL = f"SELECT channel, timestamp, json, permalink FROM {Table.PINS} WHERE channel = ? ORDER BY created_at"
    GET_PIN = f"SELECT channel, timestamp, json, permalink FROM {Table.PINS} WHERE channel = ? AND timestamp = ?"
    GET_RANDOM_PIN = f"SELECT channel, timestamp, json, permalink FROM {Table.PINS} ORDER BY RANDOM() LIMIT 1"
    GET_RANDOM_PIN_FROM_CHANNEL = f"SELECT channel, timestamp, json, permalink FROM {Table.PINS} WHERE channel = ? ORDER BY RANDOM() LIMIT 1"
    INSERT_PIN = f"INSERT INTO {Table.PINS} (created_by, channel, timestamp, json, permalink) VALUES (?, ?, ?, ?, ?)"
    MSG_LEADERBOARD = f"SELECT user_name, count(*) AS count FROM {Table.MESSAGES} WHERE lower(message) REGEXP ? AND user_name != 'Unknown' GROUP BY user_name order BY count DESC"
    MSG_MATCH = f"SELECT lower(message) FROM {Table.MESSAGES} WHERE lower(message) REGEXP ?"
    REMOVE_PIN = f"DELETE FROM {Table.PINS} WHERE channel = ? AND timestamp = ?"
