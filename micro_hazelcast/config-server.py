from flask import Flask, jsonify, request
import logging

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
)

service_registry = {
    "logging-service": [
        "logging1:50051",
        "logging2:50052",
        "logging3:50053"
    ]
}

@app.route('/config/<service_name>', methods=['GET'])
def get_service_config(service_name):
    if service_name in service_registry:
        logging.info(f"[ConfigServer] Returning configuration for {service_name}: {service_registry[service_name]}")
        return jsonify(service_registry[service_name]), 200
    else:
        logging.warning(f"[ConfigServer] Service {service_name} not found")
        return jsonify({"error": f"Service {service_name} not found"}), 404

@app.route('/config/<service_name>', methods=['POST'])
def register_service(service_name):
    data = request.json
    if not data or 'host' not in data:
        logging.warning("[ConfigServer] Host address not provided in POST request")
        return jsonify({"error": "Host address (host) is required"}), 400

    host = data['host']

    if service_name not in service_registry:
        service_registry[service_name] = []

    if host not in service_registry[service_name]:
        service_registry[service_name].append(host)
        logging.info(f"[ConfigServer] Service registered: {service_name} at {host}")
        return jsonify({"status": "Service registered successfully", "host": host}), 200
    else:
        logging.info(f"[ConfigServer] Host {host} is already registered for {service_name}")
        return jsonify({"status": "Host is already registered"}), 200

if __name__ == '__main__':
    logging.info("[ConfigServer] Starting configuration server on port 5000...")
    app.run(host="0.0.0.0", port=5000)
