#!/usr/bin/bash
set -e
cd app

rounds=0
while true
do
    rounds=$((rounds+1))
    echo "===================== Starting run $rounds"
    ./main.py
    sleep 20
done

