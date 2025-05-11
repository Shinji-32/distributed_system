import grpc
from concurrent import futures
import hazelcast
import os
import sys
import logging
import time
from messages_pb2 import LogRequest, LogResponse, MessageList, Empty
import messages_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class LoggingServiceServicer(messages_pb2_grpc.LoggingServiceServicer):
    def __init__(self, client):
        try:
            self.map = client.get_map("messages").blocking()
            logger.info("[Hazelcast] Connected and initialized the map.")
        except Exception as e:
            logger.error(f"[Hazelcast ERROR] Failed to get the map: {e}")
            sys.exit(1)

    def LogMessage(self, request, context):
        logger.info(f"[gRPC] Received message -> ID: {request.id}, Text: {request.txt}")
        if not request.id or not request.txt:
            return LogResponse(status="ID or text not provided")
        if self.map.contains_key(request.id):
            logger.warning(f"[gRPC] Message with ID {request.id} already exists.")
            return LogResponse(status="Message already stored")
        self.map.put(request.id, request.txt)
        logger.info(f"[gRPC] Message saved: {request.txt}")
        return LogResponse(status="Message successfully stored")

    def GetMessages(self, request, context):
        messages = list(self.map.values())
        logger.info(f"[gRPC] Sending all stored messages: {messages}")
        return MessageList(messages=messages)

if __name__ == "__main__":
    logger.info("[Hazelcast] Starting Hazelcast client...")
    for attempt in range(5):
        try:
            hazelcast_client = hazelcast.HazelcastClient(
                cluster_name="dev",
                cluster_members=["hazelcast1:5701", "hazelcast2:5701", "hazelcast3:5701"]
            )
            logger.info("[Hazelcast] Client started.")
            break
        except Exception as e:
            logger.warning(f"[Hazelcast] Connection attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    else:
        logger.error("[Hazelcast] Could not connect to Hazelcast after all attempts.")
        sys.exit(1)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    messages_pb2_grpc.add_LoggingServiceServicer_to_server(
        LoggingServiceServicer(hazelcast_client), server
    )

    server_port = os.environ.get("PORT", "50051")
    server.add_insecure_port(f"[::]:{server_port}")
    logger.info(f"[gRPC] Starting logging service on port {server_port}")
    server.start()
    server.wait_for_termination()
