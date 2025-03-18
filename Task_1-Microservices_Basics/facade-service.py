import grpc
from flask import Flask, request, jsonify
import uuid
import messages_pb2
import messages_pb2_grpc

app = Flask(__name__)

channel = grpc.insecure_channel('localhost:50051')
stub = messages_pb2_grpc.LoggingServiceStub(channel)

@app.route('/', methods=['POST', 'GET'])
def request_ds():
    if request.method == 'POST':
        txt = request.form.get('txt')
        if not txt:
            print("[Facade] No message provided!")
            return jsonify('No messages provided!'), 400
        
        id = str(uuid.uuid4())
        msg = messages_pb2.LogRequest(id=id, txt=txt)
        print(f"[Facade] Sending to gRPC -> ID: {id}, Text: {txt}")
        response = stub.LogMessage(msg)
        print(f"[Facade] gRPC Response -> Status: {response.status}")
        return jsonify({'id': id, 'status': response.status}), 200
    
    elif request.method == 'GET':
        response = stub.GetMessages(messages_pb2.Empty())
        print(f"[Facade] gRPC Response -> Messages: {response.messages}")
        return jsonify(response.messages), 200
    
    else:
        return jsonify('Method not allowed'), 405

if __name__ == '__main__':
    app.run(port=8880)
