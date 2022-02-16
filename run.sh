#!/usr/bin/bash
set -e
cd app

rounds=0
while true
do
    let "rounds++"
    echo "===================== Starting run $rounds"
    ./main.py
done

