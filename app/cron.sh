#!/usr/bin/env bash
if [ -z "$1" ]
then
    echo "Receiver not set!"
    exit 1
fi
output=$(./main.py 2>&1)
if [[ $? != 0 ]]
then
    echo "$output" | mail -s "Health-check-script ERROR." $1
fi
