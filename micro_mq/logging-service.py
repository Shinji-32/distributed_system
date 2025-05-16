from flask import Flask, request, jsonify
import hazelcast
import os
import logging

app = Flask(__name__)

INSTANCE_ID = os.getenv("INSTANCE_ID", "default-instance")
PORT = int(os.getenv("PORT", 8881))

app.logger.setLevel(logging.DEBUG)

client = hazelcast.HazelcastClient(
    cluster_members=["hazelcast1:5701", "hazelcast2:5701", "hazelcast3:5701"],
    cluster_name="dev"
)

log_map = client.get_map("logs").blocking()

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

if __name__ == "__main__":
    app.logger.info(f"[{INSTANCE_ID}] Starting logging service on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
