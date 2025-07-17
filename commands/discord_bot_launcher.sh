#!/bin/bash

cd "$(dirname "$0")"/../bot || exit
uv run main.py >> ../../POG-data/logging/discord_bot.out 2>&1
