from flask import Flask, request, jsonify
import hazelcast
import os
import logging
import socket
import consul

# -----------------------------------------------
# Реєстрація сервісу в Consul
# -----------------------------------------------
def register_service(service_name, service_id, port):
    ip = socket.gethostbyname(socket.gethostname())
    c = consul.Consul(host="consul", port=8500)
    c.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=ip,
        port=port,
        check=consul.Check.tcp(ip, port, interval="10s")
    )

# -----------------------------------------------
# Отримання конфігурації з Consul KV
# -----------------------------------------------
def get_kv_config(key):
    c = consul.Consul(host="consul", port=8500)
    _, data = c.kv.get(key)
    if data and "Value" in data:
        return data["Value"].decode()
    return None

# -----------------------------------------------
# Flask App
# -----------------------------------------------
app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

INSTANCE_ID = os.getenv("INSTANCE_ID", "logging-1")
PORT = int(os.getenv("PORT", 5001))

# Реєструємо сервіс
register_service("logging-service", INSTANCE_ID, PORT)

# -----------------------------------------------
# Ініціалізація Hazelcast на основі Consul KV
# -----------------------------------------------
members_config = get_kv_config("hazelcast/members")
cluster_members = members_config.split(",") if members_config else ["hazelcast1:5701"]

client = hazelcast.HazelcastClient(
    cluster_members=cluster_members,
    cluster_name="dev"
)

log_map = client.get_map("logs").blocking()

# -----------------------------------------------
# Endpoint для логів
# -----------------------------------------------
@app.route("/tracker", methods=["POST", "GET"])
def tracker_handler():
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            key = data.get("msg")
            value = data.get("msg")
        else:
            key = request.form.get("key")
            value = request.form.get("data")

        if not key or not value:
            return jsonify({"error": "Missing required 'key' or 'data'"}), 400

        if log_map.contains_key(key):
            app.logger.info(f"[{INSTANCE_ID}] Duplicate message ignored: {key}")
            return jsonify({"status": "Duplicate entry"}), 201

        log_map.put(key, value)
        app.logger.info(f"[{INSTANCE_ID}] New log stored: {value} (key: {key})")
        return jsonify({"status": "Stored successfully"}), 201

    elif request.method == "GET":
        all_values = log_map.values()
        return jsonify({"messages": list(all_values)}), 200

# -----------------------------------------------
# Запуск Flask
# -----------------------------------------------
if __name__ == "__main__":
    app.logger.info(f"[{INSTANCE_ID}] Starting logging service on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
