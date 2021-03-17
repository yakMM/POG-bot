#!/bin/bash

cd "$(dirname "$0")"/../bot || exit
python3 -u main.py > ../../POG-data/logging/discord_bot.out 2>&1
