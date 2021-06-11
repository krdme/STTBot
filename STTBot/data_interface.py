# External
import sqlite3
import json

# Internal
from STTBot.utils import env


db = env.get_cfg("PATH_DB")


def get_cur():
    con = sqlite3.connect(db, isolation_level=None)
    return con.cursor()


# - PINS - #


def get_pin(channel, timestamp):
    cur = get_cur()
    cur.execute(Query.GET_PIN, (channel, timestamp))
    row = cur.fetchone()
    cur.close()

    if row is None:
        return None
    else:
        return row[0], row[1], json.loads(row[2])


def get_random_pin():
    cur = get_cur()
    cur.execute(Query.GET_RANDOM_PIN)
    row = cur.fetchone()
    cur.close()

    if row is None:
        return None
    else:
        return row[0], row[1], json.loads(row[2])


def get_all_pins():
    cur = get_cur()
    cur.execute(Query.GET_ALL_PINS)
    rows = cur.fetchall()
    cur.close()

    if len(rows) == 0:
        return None
    else:
        return [[row[0], row[1], json.loads(row[2])] for row in rows]


def insert_pin(user, channel, timestamp, message_json):
    cur = get_cur()
    cur.execute(Query.INSERT_PIN, (user, channel, timestamp, message_json))
    cur.close()


def remove_pin(channel, timestamp):
    cur = get_cur()
    cur.execute(Query.REMOVE_PIN, (channel, timestamp))
    cur.close()


# - AUTH - #


def insert_token(team_id, token):
    cur = get_cur()
    cur.execute(Query.INSERT_TOKEN, (team_id, token))
    cur.close()


def get_all_tokens():
    cur = get_cur()
    cur.execute(Query.GET_ALL_TOKENS)
    rows = cur.fetchall()
    cur.close()
    tokens = {}

    for row in rows:
        tokens[row[0]] = row[1]

    return tokens


# - CONSTANTS - #


class Table:
    PINS = "pins"
    TOKENS = "tokens"


class Query:
    GET_ALL_PINS = f"SELECT channel, timestamp, json FROM {Table.PINS} ORDER BY created_at"
    GET_ALL_TOKENS = f"SELECT team_id, token FROM {Table.TOKENS}"
    GET_PIN = f"SELECT channel, timestamp, json FROM {Table.PINS} WHERE channel = ? AND timestamp = ?"
    GET_RANDOM_PIN = f"SELECT channel, timestamp, json FROM {Table.PINS} ORDER BY RANDOM() LIMIT 1"
    INSERT_PIN = f"INSERT INTO {Table.PINS} (created_by, channel, timestamp, json) VALUES (?, ?, ?, ?)"
    INSERT_TOKEN = f"REPLACE INTO {Table.TOKENS} (team_id, token) VALUES (?, ?)"
    REMOVE_PIN = f"DELETE FROM {Table.PINS} WHERE channel = ? AND timestamp = ?"
