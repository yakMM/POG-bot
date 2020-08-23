#!/bin/bash
cd "$(dirname "$0")"

pkill -f main.py
rm -f running
echo "Bot stopped..."
