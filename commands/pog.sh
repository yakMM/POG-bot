#!/bin/bash


SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

function my_help
{
  # Display Help
  echo
  echo "Usage:"
  echo "pog help              Display help prompt."
  echo "pog start             Start the launcher and the bots."
  echo "pog stop              Stop the launcher and the bots."
  echo "pog restart           Restart the launcher and the bots."
  echo "pog ts3 restart       Restart the TS3 bot."
  echo "pog discord restart   Restart the discord bot."
  echo "pog update            Stop the bots and update the files from github."
  echo "pog ts3 log           Display the last lines of the TS3 bot log file."
  echo "pog discord log       Display the last lines of the discord bot log file."
  echo
}

function my_error
{
  # On error
  echo "Error occurred!"
  exit
}

function my_stop
{
  # Stop bot
  cd "$SCRIPT_DIR" || my_error

  pkill -SIGINT -f pog_launcher.py
  rm -f running
  echo "Bot stopped..."
}

function my_start
{
  # Start bot
  cd "$SCRIPT_DIR/.." || my_error

  if [ -f "commands/running" ]; then
    echo "Bot is already running!"
  else
    touch commands/running
    mkdir -p ../POG-data
    mkdir -p ../POG-data/logging
    mkdir -p ../POG-data/matches
    nohup python3.11 -u commands/pog_launcher.py >> ../POG-data/logging/launcher.out 2>&1 &
    echo "Bot started..."
  fi
}

function my_ts3_restart
{
  cd "$SCRIPT_DIR" || my_error

  if [ -f "running" ]; then
    pkill -SIGUSR1 -f pog_launcher.py
    echo "Restarting TS3 bot!"
  else
    echo "Launcher is not running! Use [pog start] first!"  >&2
  fi
}

function my_discord_restart
{
  cd "$SCRIPT_DIR" || my_error

  if [ -f "running" ]; then
    pkill -SIGUSR2 -f pog_launcher.py
    echo "Restarting discord bot!"
  else
    echo "Launcher is not running! Use [pog start] first!"  >&2
  fi
}

function my_update
{
  # Update code from github
  cd "$SCRIPT_DIR/.." || my_error
  git clean -xdf
  git fetch origin master
  git reset --hard origin/master

  chmod a+x commands/*
  cp ../POG-data/secret/* bot/
  python3.11 -m pdm install --prod
}

function my_discord_log
{
  # Show last logs
  cd "$SCRIPT_DIR/.." || my_error
  tail ../POG-data/logging/bot_log
}

function my_ts3_log
{
  # Show last logs
  cd "$SCRIPT_DIR/.." || my_error
  tail ../POG-data/logging/ts3_bot.out
}

if [ $# -eq 0 ]; then
  my_help
  exit
fi
if [ $# -eq 1 ]; then
  if [ "$1" == "help" ]; then
    my_help
    exit
  fi
  if [ "$1" == "start" ]; then
    my_start
    exit
  fi
  if [ "$1" == "stop" ]; then
    my_stop
    exit
  fi
  if [ "$1" == "restart" ]; then
    my_stop
    my_start
    exit
  fi
  if [ "$1" == "update" ]; then
    my_stop
    my_update
    my_start
    exit
  fi
fi
if [ $# -eq 2 ]; then
  if [ "$1" == "ts3" ] && [ "$2" == "restart" ]; then
    my_ts3_restart
    exit
  fi
  if [ "$1" == "discord" ] && [ "$2" == "restart" ]; then
    my_discord_restart
    exit
  fi
  if [ "$1" == "ts3" ] && [ "$2" == "log" ]; then
    my_ts3_log
    exit
  fi
  if [ "$1" == "discord" ] && [ "$2" == "log" ]; then
    my_discord_log
    exit
  fi
fi
echo "Invalid command!" >&2
my_help
exit



