FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install grpcio grpcio-tools hazelcast-python-client flask

CMD ["python", "logging-service.py"]
