#source .env
. .env/bin/activate
export SECRETS_DIR=./secrets/
mkdir -p logs
python src/app.py > logs/nb_$(date +"%Y%m%d-%H%M%S").log 2>&1 &
