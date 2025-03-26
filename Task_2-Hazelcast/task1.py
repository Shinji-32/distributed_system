import hazelcast


hz_client = hazelcast.HazelcastClient(
    cluster_name="secure-cluster",
    cluster_members=["localhost:5701", "localhost:5702", "localhost:5703"]
)


shared_map = hz_client.get_map("distributed-cache").blocking()


for index in range(1000):
    shared_map.put(f"key_{index}", f"data_{index}")

print("Дані успішно додані до розподіленої мапи.")
print(f"Кількість записів у мапі: {shared_map.size()}")


hz_client.shutdown()
