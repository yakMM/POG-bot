#!/bin/bash
cd "$(dirname "$0")"

if [ -f "running" ]; then
	echo "Bot is already running!"
else
	touch running
    mkdir -p ../logging
	cd ../bot/
	nohup python3 -u main.py > ../logging/bot_console.out 2>&1 &
	echo "Bot started..."
fi

