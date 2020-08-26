#!/bin/bash

function my_help
{
    # Display Help
    echo
    echo "Usage:"
    echo "pog help        Display help prompt."
    echo "pog start       Start the POG bot."
    echo "pog stop        Stop the POG bot."
    echo "pog restart     Restart the POG bot."
    echo "pog update      Stop the POG bot and update the files from github"
    echo
}

function my_stop
{
    # Stop bot
    cd "$(dirname "$0")"

    pkill -f main.py
    rm -f running
    echo "Bot stopped..."
}

function my_start
{
    # Start bot
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
}

function my_update
{
    # Update code from github
    cd "$(dirname "$0")"
    cd ..
    git clean -xdf
    git fetch --all
    git reset --hard

    chmod a+x commands/*
    cp ../secret/* bot/
}

if [ $# -ne 1 ]; then
    echo "Invalid command!"
    my_help
    exit
fi
if [ $1 == "help" ]; then
    my_help
    exit
fi
if [ $1 == "start" ]; then
    my_start
    exit
fi
if [ $1 == "stop" ]; then
    my_stop
    exit
fi
if [ $1 == "restart" ]; then
    my_stop
    my_start
    exit
fi
if [ $1 == "update" ]; then
    my_stop
    my_update
    exit
fi
echo "Invalid command!"
my_help
exit



