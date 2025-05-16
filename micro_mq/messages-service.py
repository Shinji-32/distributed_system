from flask import Flask, jsonify
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
import json
import threading
import os
import time

app = Flask(__name__)
INSTANCE_ID = os.getenv("INSTANCE_ID", "default-instance")
PORT = int(os.getenv("PORT", 8890))

received_messages = []

def kafka_listener():
    for attempt in range(10):
        try:
            consumer = KafkaConsumer(
                "messages",
                bootstrap_servers=["kafka1:9092", "kafka2:9093", "kafka3:9094"],
                auto_offset_reset="earliest",
                group_id=f"consumer-group-{INSTANCE_ID}",
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            print(f"[{INSTANCE_ID}] Connected to Kafka brokers", flush=True)
            break
        except NoBrokersAvailable:
            print(f"[{INSTANCE_ID}] Kafka brokers unavailable (try {attempt+1}/10). Retrying in 5 seconds...", flush=True)
            time.sleep(5)
    else:
        raise RuntimeError(f"[{INSTANCE_ID}] Could not connect to Kafka after multiple attempts")

    print(f"[{INSTANCE_ID}] Kafka consumer started", flush=True)
    for message in consumer:
        text = message.value.get("msg")
        if text:
            received_messages.append(text)
            print(f"[{INSTANCE_ID}] Consumed message: {text}", flush=True)

@app.route("/messages", methods=["GET"])
def fetch_messages():
    return jsonify({"messages": received_messages})

if __name__ == "__main__":
    print(f"[{INSTANCE_ID}] Service starting on port {PORT}", flush=True)
    threading.Thread(target=kafka_listener, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
