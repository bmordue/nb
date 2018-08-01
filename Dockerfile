FROM python:2.7

WORKDIR /workspace

COPY src .

RUN pip install -r requirements.txt

CMD ["python", "./app.py"]
