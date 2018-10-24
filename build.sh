cd src
docker build -t nb:$(git rev-parse --short HEAD) -t nb:latest .
cd -
