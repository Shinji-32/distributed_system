import grpc
from flask import Flask, request, jsonify
import uuid
import random
import messages_pb2
import messages_pb2_grpc
import logging
import requests

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
)

app = Flask(__name__)

CONFIG_SERVER_URL = "http://config-server:5000/config"

# Function to get service configuration
def get_service_hosts(service_name):
    try:
        response = requests.get(f"{CONFIG_SERVER_URL}/{service_name}")
        if response.status_code == 200:
            return response.json()  # Returns list of hosts (e.g., ["logging1:50051"])
        else:
            logging.error(f"[Facade] Failed to get configuration for {service_name}: {response.text}")
            return []
    except Exception as e:
        logging.error(f"[Facade] Error retrieving configuration from config-server: {e}")
        return []

# Function to check if a service is alive
def is_service_alive(host, port):
    try:
        with grpc.insecure_channel(f"{host}:{port}") as channel:
            grpc.channel_ready_future(channel).result(timeout=1)
            return True
    except Exception as e:
        logging.warning(f"[Facade] Service unavailable at {host}:{port}: {e}")
        return False

# Function to get gRPC stub
def get_grpc_stub(service_name):
    hosts = get_service_hosts(service_name)
    if not hosts:
        raise Exception(f"No available instances of {service_name}.")

    random.shuffle(hosts)
    for host_port in hosts:
        host, port = host_port.split(':')
        if not is_service_alive(host, port):
            logging.warning(f"[Facade] Skipping unreachable {service_name} at {host_port}")
            continue
        try:
            channel = grpc.insecure_channel(host_port)
            if service_name == "logging-service":
                return messages_pb2_grpc.LoggingServiceStub(channel)
        except Exception as e:
            logging.warning(f"[Facade] Failed to connect to {service_name} at {host_port}: {e}")
    raise Exception(f"No healthy instances of {service_name} found.")

@app.route('/', methods=['POST', 'GET'])
def request_ds():
    try:
        logging_stub = get_grpc_stub("logging-service")
    except Exception as e:
        logging.error(f"[Facade] Error: {e}")
        return jsonify({'error': str(e)}), 503

    if request.method == 'POST':
        txt = request.form.get('txt')
        if not txt:
            logging.warning("[Facade] No message text provided in POST request")
            return jsonify('No message provided!'), 400
        id = str(uuid.uuid4())
        msg = messages_pb2.LogRequest(id=id, txt=txt)
        response = logging_stub.LogMessage(msg)
        logging.info(f"[Facade] Sent message: ID={id}, Status={response.status}")
        return jsonify({'id': id, 'status': response.status}), 200

    elif request.method == 'GET':
        response = logging_stub.GetMessages(messages_pb2.Empty())
        messages = list(response.messages)
        logging.info(f"[Facade] Retrieved {len(messages)} messages.")
        return jsonify(messages), 200

    else:
        logging.warning("[Facade] Method not allowed")
        return jsonify('Method not allowed'), 405

if __name__ == '__main__':
    logging.info("[Facade] Starting facade service on port 8880...")
    app.run(host='0.0.0.0', port=8880)
