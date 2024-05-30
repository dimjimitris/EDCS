import client_logic as cl
import global_variables as gv
import time
import threading as th

sleep_time = (gv.LEASE_TIMEOUT + 1) // 2

def test_forgotten_locks():
    def acquire_lock_thread():
        client = cl.Client(gv.SERVERS[0])
        client.connect()
        resp = client.acquire_lock(0)
        print(f"Acquire lock response: {resp}")
        client.disconnect()

    def re_acquire_lock_thread():
        time.sleep(sleep_time)
        client = cl.Client(gv.SERVERS[0])
        client.connect()
        resp = client.acquire_lock(0)
        print(f"Re-acquire lock response: {resp}")
        client.disconnect()

    threads = [
        th.Thread(target=acquire_lock_thread),
        th.Thread(target=re_acquire_lock_thread),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    test_forgotten_locks()