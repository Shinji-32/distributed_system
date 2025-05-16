import random
import requests
from flask import Flask, request, jsonify
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
import json
import time

app = Flask(__name__)

CONFIG_SERVER = "http://config-server:8888"
KAFKA_SERVERS = ["kafka1:9092", "kafka2:9093", "kafka3:9094"]
TOPIC = "messages"

def connect_kafka(max_attempts=10, wait_seconds=5):
    for attempt in range(1, max_attempts + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_SERVERS,
                value_serializer=lambda val: json.dumps(val).encode('utf-8')
            )
            print(f"[Facade] Kafka connection established on attempt {attempt}")
            return producer
        except NoBrokersAvailable:
            print(f"[Facade] Kafka unavailable (attempt {attempt}/{max_attempts}), retrying in {wait_seconds}s...")
            time.sleep(wait_seconds)
    raise RuntimeError("[Facade] Could not connect to Kafka after multiple attempts")

producer = connect_kafka()

def fetch_service_endpoints(service):
    try:
        resp = requests.get(f"{CONFIG_SERVER}/services/{service}", timeout=2)
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception as err:
        print(f"[Facade] Error fetching {service} endpoints: {err}")
        return []

def call_service_instance(service, endpoint, method="GET", payload=None):
    instances = fetch_service_endpoints(service)
    random.shuffle(instances)
    for base_url in instances:
        full_url = f"{base_url}{endpoint}"
        try:
            if method.upper() == "POST":
                res = requests.post(full_url, json=payload, timeout=3)
            else:
                res = requests.get(full_url, timeout=3)
            if res.status_code in (200, 201):
                return res.json()
        except Exception as exc:
            print(f"[Facade] Warning: unable to reach {full_url} - {exc}")
    return {"error": "No available instances"}, 500

@app.route("/entry", methods=["POST"])
def create_entry():
    data = request.json or {}
    message = data.get("msg")
    if not message:
        return jsonify({"error": "Field 'msg' is required"}), 400

 
    producer.send(TOPIC, {"txt": message})
    producer.flush()
    print(f"[Facade] Message sent to Kafka: {message}")

    
    result = call_service_instance("logging-service", "/tracker", method="POST", payload={"txt": message})
    if "error" in result:
        print(f"[Facade] Failed to send to logging-service: {result.get('error')}")
        return jsonify({"error": "Unable to save message in logging-service"}), 500

    return jsonify({"status": "Message successfully sent to Kafka and logging-service"}), 201

@app.route("/entry", methods=["GET"])
def get_entries():
    return call_service_instance("logging-service", "/tracker")

@app.route("/notify", methods=["GET"])
def get_notifications():
    return call_service_instance("messages-service", "/messages")

@app.route("/combined", methods=["GET"])
def combined_messages():
    log_resp = call_service_instance("logging-service", "/tracker")
    logs = log_resp.get("messages", []) if "error" not in log_resp else []

    msg_resp = call_service_instance("messages-service", "/messages")
    msgs = msg_resp.get("messages", []) if "error" not in msg_resp else []

    combined = list(set(logs + msgs))
    return jsonify({"messages": combined})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8880)
