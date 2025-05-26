import random
import requests
from flask import Flask, request, jsonify
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
import json
import time
import os
from consul import Consul

app = Flask(__name__)

CONFIG_SERVER = os.getenv("CONFIG_SERVER", "http://config-server:8888")
KAFKA_SERVERS = os.getenv("KAFKA_SERVERS", "kafka1:9092,kafka2:9093,kafka3:9094").split(",")
TOPIC = os.getenv("KAFKA_TOPIC", "messages")
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", 8500))


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


def discover_service(service_name):
    try:
        c = Consul(host=CONSUL_HOST, port=CONSUL_PORT)
        services = c.health.service(service_name, passing=True)[1]
        if services:
            instance = random.choice(services)['Service']
            return f"http://{instance['Address']}:{instance['Port']}"
    except Exception as e:
        print(f"[Facade] Error discovering service {service_name}: {e}")
    return None


def call_service_instance(service_name, endpoint, method="GET", payload=None):
    base_url = discover_service(service_name)
    if not base_url:
        return {"error": "No available instances"}, 500

    full_url = f"{base_url}{endpoint}"
    try:
        if method.upper() == "POST":
            res = requests.post(full_url, json=payload, timeout=3)
        else:
            res = requests.get(full_url, timeout=3)
        if res.status_code in (200, 201):
            return res.json()
        else:
            return {"error": f"Service responded with status {res.status_code}"}, res.status_code
    except Exception as exc:
        print(f"[Facade] Warning: unable to reach {full_url} - {exc}")
        return {"error": "Service unreachable"}, 500


@app.route("/entry", methods=["POST"])
def create_entry():
    data = request.json or {}
    message = data.get("msg")
    if not message:
        return jsonify({"error": "Field 'msg' is required"}), 400

    producer.send(TOPIC, {"txt": message})
    producer.flush()
    print(f"[Facade] Message sent to Kafka: {message}")

    result, status = call_service_instance("logging-service", "/tracker", method="POST", payload={"msg": message})
    if "error" in result:
        print(f"[Facade] Failed to send to logging-service: {result.get('error')}")
        return jsonify(result), status

    return jsonify({"status": "Message successfully sent to Kafka and logging-service"}), 201


@app.route("/entry", methods=["GET"])
def get_entries():
    result, status = call_service_instance("logging-service", "/tracker")
    return jsonify(result), status


@app.route("/notify", methods=["GET"])
def get_notifications():
    result, status = call_service_instance("messages-service", "/messages")
    return jsonify(result), status


@app.route("/combined", methods=["GET"])
def combined_messages():
    log_resp, _ = call_service_instance("logging-service", "/tracker")
    logs = log_resp.get("messages", []) if isinstance(log_resp, dict) and "error" not in log_resp else []

    msg_resp, _ = call_service_instance("messages-service", "/messages")
    msgs = msg_resp.get("messages", []) if isinstance(msg_resp, dict) and "error" not in msg_resp else []

    combined = list(set(logs + msgs))
    return jsonify({"messages": combined})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8880)
