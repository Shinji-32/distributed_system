import hazelcast
import threading
import time


client = hazelcast.HazelcastClient(
    cluster_name="secure-cluster",
    cluster_members=["localhost:5701", "localhost:5702", "localhost:5703"]
)

task_queue = client.get_queue("task-queue").blocking()
producer_done = False
stop_flag = False


def producer():
    global producer_done
    print("Продюсер розпочав запис завдань...")
    for num in range(1, 101):
        task_queue.put(num)
        print(f"Додано завдання {num}, поточний розмір черги: {task_queue.size()}")
        time.sleep(0.05)
    print("Продюсер завершив запис")
    producer_done = True


def consumer(consumer_id):
    print(f"Споживач {consumer_id} розпочав обробку завдань")
    while not producer_done or task_queue.size() > 0:
        task = task_queue.poll(timeout=1.0)
        if task is None:
            if producer_done and task_queue.size() == 0:
                break
            continue
        print(f"Споживач {consumer_id} обробив завдання: {task}, залишилось у черзі: {task_queue.size()}")
    print(f"Споживач {consumer_id} завершив роботу")


def test_full_queue():
    global stop_flag
    print("\nТестування поведінки при повній черзі...")
    task_queue.clear()
    print("Черга очищена")

    for num in range(1, 11):
        task_queue.put(num)
        print(f"Записано у тестову чергу: {num}, поточний розмір: {task_queue.size()}")

    def try_insert():
        try:
            task_queue.put(999)
            print("Несподівано: додано 999 у повну чергу")
        except Exception as e:
            if not stop_flag:
                print(f"Помилка при вставці у повну чергу: {e}")

    print("Спроба вставки елемента у повну чергу (має заблокуватись)...")
    insert_thread = threading.Thread(target=try_insert)
    insert_thread.daemon = True
    insert_thread.start()

    time.sleep(5)
    if insert_thread.is_alive():
        print("Очікувано: вставка блокується")
    else:
        print("Несподівано: вставка не заблокувалась")

    stop_flag = True

if __name__ == "__main__":
    print("Запуск демо-програми з продюсером і споживачами")
    prod_thread = threading.Thread(target=producer)
    cons_thread_1 = threading.Thread(target=consumer, args=(1,))
    cons_thread_2 = threading.Thread(target=consumer, args=(2,))

    prod_thread.start()
    cons_thread_1.start()
    cons_thread_2.start()

    prod_thread.join()
    cons_thread_1.join()
    cons_thread_2.join()

    test_full_queue()
    client.shutdown()
    print("\nДемонстрація завершена")
