FROM python:3.10-slim-bullseye

WORKDIR /workspace

COPY ./requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app.py"]
