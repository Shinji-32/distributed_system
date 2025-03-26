import hazelcast
import threading
import time



def increment_no_lock(shared_map, iterations):
    for _ in range(iterations):
        current = shared_map.get("counter") or 0
        shared_map.put("counter", current + 1)



def increment_optimistic(shared_map, iterations):
    for _ in range(iterations):
        while True:
            old_value = shared_map.get("counter") or 0
            new_value = old_value + 1
            if shared_map.replace_if_same("counter", old_value, new_value):
                break



def increment_pessimistic(shared_map, iterations):
    for _ in range(iterations):
        shared_map.lock("counter")
        try:
            current = shared_map.get("counter") or 0
            shared_map.put("counter", current + 1)
        finally:
            shared_map.unlock("counter")



def run_test(method, shared_map, thread_count, iterations):
    print(f"\n--- Тест: {method} ---")
    shared_map.put("counter", 0)

    start_time = time.time()
    threads = [threading.Thread(target=method, args=(shared_map, iterations)) for _ in range(thread_count)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    elapsed = time.time() - start_time
    final_value = shared_map.get("counter")
    expected_value = thread_count * iterations

    print(f"Фінальне значення: {final_value}, Очікуване: {expected_value}")
    print(f"Час виконання: {elapsed:.2f} сек\n")


if __name__ == "__main__":
    client = hazelcast.HazelcastClient(
        cluster_name="secure-cluster",
        cluster_members=["localhost:5701", "localhost:5702", "localhost:5703"]
    )

    distributed_map = client.get_map("counter_map").blocking()
    num_threads = 3
    num_iterations = 10_000

    #run_test(increment_no_lock, distributed_map, num_threads, num_iterations)
    #run_test(increment_optimistic, distributed_map, num_threads, num_iterations)
    run_test(increment_pessimistic, distributed_map, num_threads, num_iterations)

    client.shutdown()
