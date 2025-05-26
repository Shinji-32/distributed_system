from flask import Flask, jsonify
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
import json
import threading
import os
import time
from consul import Consul
import socket

app = Flask(__name__)

INSTANCE_ID = os.getenv("INSTANCE_ID", "default-instance")
PORT = int(os.getenv("PORT", 8890))
KAFKA_SERVERS = os.getenv("KAFKA_SERVERS", "kafka1:9092,kafka2:9093,kafka3:9094").split(",")
TOPIC = os.getenv("KAFKA_TOPIC", "messages")
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", 8500))

received_messages = set()

def register_with_consul():
    consul = Consul(host=CONSUL_HOST, port=CONSUL_PORT)
    ip = socket.gethostbyname(socket.gethostname())
    service_id = f"{INSTANCE_ID}-{PORT}"

    consul.agent.service.register(
        name="messages-service",
        service_id=service_id,
        address=ip,
        port=PORT,
        check={
            "http": f"http://{ip}:{PORT}/messages",
            "interval": "10s"
        }
    )
    print(f"[{INSTANCE_ID}] Registered with Consul as '{service_id}'")

def kafka_listener():
    for attempt in range(1, 11):
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_SERVERS,
                auto_offset_reset="earliest",
                group_id=f"consumer-group-{INSTANCE_ID}",
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            print(f"[{INSTANCE_ID}] Connected to Kafka (attempt {attempt})", flush=True)
            break
        except NoBrokersAvailable:
            print(f"[{INSTANCE_ID}] Kafka unavailable (attempt {attempt}), retrying in 5s...", flush=True)
            time.sleep(5)
    else:
        raise RuntimeError(f"[{INSTANCE_ID}] Could not connect to Kafka after 10 attempts")

    for message in consumer:
        text = message.value.get("msg")
        if text:
            received_messages.add(text)
            print(f"[{INSTANCE_ID}] Consumed: {text}", flush=True)

@app.route("/messages", methods=["GET"])
def fetch_messages():
    return jsonify({"messages": list(received_messages)})

if __name__ == "__main__":
    print(f"[{INSTANCE_ID}] Starting messages service on port {PORT}", flush=True)
    register_with_consul()
    threading.Thread(target=kafka_listener, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
