#!/bin/bash
echo "Wait..."
sleep 10
curl -X PUT -d '["kafka-1:9092", "kafka-2:9093", "kafka-3:9094"]' http://consul:8500/v1/kv/config/kafka/brokers
curl -X PUT -d '"msg_kafka"' http://consul:8500/v1/kv/config/kafka/topic
curl -X PUT -d '["hz-1:5701", "hz-2:5701", "hz-3:5701"]' http://consul:8500/v1/kv/config/hazelcast/cluster_members
curl -X PUT -d '"dev"' http://consul:8500/v1/kv/config/hazelcast/cluster_name
