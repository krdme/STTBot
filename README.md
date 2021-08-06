# STTBot

A simple Slack bot used for the STT chat built on top of the [Bolt framework](https://github.com/SlackAPI/bolt-python)

# Getting started

1. Register your app as described in [Building an app with Bolt for Python](https://api.slack.com/start/building/bolt-python#start).
2. Get the bot
   ```bash
   git -C ~/sttbot/ clone git@github.com:krdme/STTBot.git
   ```
3. From the Slack Developer page, add the following keys to the `.env.example.json` file and rename the file to `.env.prod.json`:
   `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SCOPES`, `SLACK_SIGNING_SECRET`
4. Create a sqlite3 database and set the `PATH_DB` in `.env.prod.json` to match
   ```bash
   sqlite3 ~/sttbot/sttbot.db
   sqlite> CREATE TABLE pins ( created_by text not null, channel text not null, timestamp text not null, created_at datetime DEFAULT CURRENT_TIMESTAMP not null, json text, permalink text, primary key ( channel, timestamp) );
   ```
5. Run the bot with the following:
    ```bash
    python3.7 ~/sttbot/start.py
    ```

The bot is now listening on port 3000 locally. You can use a tool like ngrok as described in the aforementioned Slack blog post to connect this up to the Slack events subscription API.

# Running with Docker

Assuming your source code is in `~/sttbot/` and your sqlite3 database is in `~/db/`:

1. Update your `.env.prod.json` to have `PATH_DB` point to `/db/sttbot.db` and `SERVER_HOST` point to `0.0.0.0`. The former must match where you mount the database volume in step 2 and the latter ensures your app listens to requests coming from outwith the Docker container.
2. Run the following
    ```bash
    docker build -t sttbot ~/sttbot/
    docker run -d -v ~/sttbot_db:/db --name sttbot -p 3000:3000 --restart unless-stopped sttbot
    ```
