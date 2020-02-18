#source .env
python src/app.py > nb_$(date +"%Y%m%d-%H%M%S").log 2>&1
