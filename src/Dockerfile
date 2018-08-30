FROM python:2.7

WORKDIR /workspace

COPY ./requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app.py"]
