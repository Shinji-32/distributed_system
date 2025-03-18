import grpc
from concurrent import futures
import time
from messages_pb2 import LogRequest, LogResponse, MessageList, Empty
import messages_pb2_grpc

class LoggingServiceServicer(messages_pb2_grpc.LoggingServiceServicer):
    def __init__(self):
        self.msg = {}
        self.processed_ids = set()
    
    def LogMessage(self, request, context):
        print(f"[gRPC] Received message -> ID: {request.id}, Text: {request.txt}")
        
        if not request.id or not request.txt:
            return LogResponse(status="No id or text provided")
        
        if request.id in self.processed_ids:
            return LogResponse(status="Message already logged")
        
        self.msg[request.id] = request.txt
        self.processed_ids.add(request.id)
        print(f"[gRPC] Stored message: {request.txt}")
        return LogResponse(status="Message was logged successfully")
    
    def GetMessages(self, request, context):
        print(f"[gRPC] Sending all stored messages: {self.msg.values()}")
        return MessageList(messages=list(self.msg.values()))

server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
messages_pb2_grpc.add_LoggingServiceServicer_to_server(LoggingServiceServicer(), server)
server.add_insecure_port('[::]:50051')
server.start()
print("Logging Service started on port 50051")
server.wait_for_termination()

