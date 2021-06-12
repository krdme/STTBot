# STTBot

A simple Slack bot used for the STT chat built on top of the [Bolt framework](https://github.com/SlackAPI/bolt-python)

# Getting started

1. Register your app as described in [Building an app with Bolt for Python](https://api.slack.com/start/building/bolt-python#start). 
2. From the Slack Developer page, add the following keys to the `.env.example.json` file and rename the file to `.env.prod.json`:
   `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SCOPES`, `SLACK_SIGNING_SECRET`
3. Run the bot with the following:
    ```bash
    git -C ~/ clone git@github.com:krdme/STTBot.git
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
