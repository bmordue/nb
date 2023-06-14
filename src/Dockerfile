FROM python:3.11.0rc2-slim

WORKDIR /workspace

COPY ./requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app.py"]
