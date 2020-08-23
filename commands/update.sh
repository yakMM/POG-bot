#!/bin/bash
cd "$(dirname "$0")"

./stop.sh
git reset --hard
git clean -xdf
git pull

chmod a+x *
