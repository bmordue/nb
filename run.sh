#!/bin/bash
. .env/bin/activate
export SECRETS_DIR=./secrets/
mkdir -p logs
#kill $(cat pid)
#rm -f pid
python src/app.py > logs/nb_$(date +"%Y%m%d-%H%M%S").log 2>&1 &
#echo &! > pid
