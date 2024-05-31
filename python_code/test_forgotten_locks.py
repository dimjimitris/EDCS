import requests
import global_variables as gv
import time
import threading as th

sleep_time = (gv.LEASE_TIMEOUT + 1) // 2
CLIENT_API = gv.CLIENT_API

def acquire_lock():
    data = {
        'client_id': 0,
        'command': 'lock',
        'mem_address': 0
    }
    requests.post(f'http://{CLIENT_API}/connect', data={'client_id': 0, 'server_index': 0})
    response = requests.post(f'http://{CLIENT_API}/command', data=data)
    print(f"Acquire lock response: {response.json()['response']}")
    requests.post(f'http://{CLIENT_API}/disconnect', data={'client_id': 0})

def re_acquire_lock():
    time.sleep(sleep_time)
    data = {
        'client_id': 0,
        'command': 'lock',
        'mem_address': 0
    }
    requests.post(f'http://{CLIENT_API}/connect', data={'client_id': 0, 'server_index': 0})
    response = requests.post(f'http://{CLIENT_API}/command', data=data)
    print(f"Re-acquire lock response: {response.json()['response']}")
    requests.post(f'http://{CLIENT_API}/disconnect', data={'client_id': 0})


def test_forgotten_locks():
    threads = [
        th.Thread(target=acquire_lock),
        th.Thread(target=re_acquire_lock),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    test_forgotten_locks()
