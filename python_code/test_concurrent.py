import requests
import threading as th
import json

import global_variables as gv
import time


SERVERS = gv.SERVERS
CLIENT_API = gv.CLIENT_API

def test_reads_after_write(thread_cnt, local):
    # Connect to the local server to perform the initial write
    client_id = 0
    requests.post(f'http://{CLIENT_API}/connect', data={'client_id': client_id, 'server_index': 0})
    data = {'client_id': client_id, 'command': 'write', 'mem_address': 0, 'data': 0}
    response = requests.post(f'http://{CLIENT_API}/command', data=data)
    print(f"Initial write response from local server: {response.json()['response']}")
    requests.post(f'http://{CLIENT_API}/disconnect', data={'client_id': 0})

    local_server = 0
    remote_server = 1
    # Choose the server to read from based on the 'local' flag
    server = local_server if local else remote_server

    # Create clients for each thread
    clients = [server for _ in range(thread_cnt - 1)]
    clients.append(local_server)

    for client_id, server_index in enumerate(clients):
        requests.post(f'http://{CLIENT_API}/connect', data={'client_id': client_id, 'server_index': server_index})

    results = [-1 for i in range(thread_cnt - 1)]

    # Function to perform read operation
    def read_thread(idx):
        data = {
            'client_id': idx,
            'command': 'read',
            'mem_address':  0
        }
        response = requests.post(f'http://{CLIENT_API}/command', data=data)
        result = response.json()['response']
        results[idx] = result

    # Function to perform write operation
    def write_thread(idx):
        data = {
            'client_id': idx,
            'command': 'write',
            'mem_address': 0,
            'data': 1
        }
        requests.post(f'http://{CLIENT_API}/command', data=data)

    # Create threads for read and write operations
    threads = [th.Thread(target=read_thread, args=(i,)) for i in range(thread_cnt - 1)]
    threads.append(th.Thread(target=write_thread, args=(thread_cnt - 1,)))

    # Start and join threads
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # Validate the results
    for i in range(len(results)):
        for j in range(len(results)):
            if results[i]["wtag"] > results[j]["wtag"]:
                assert results[i]["data"] > results[j]["data"]
            if results[i]["wtag"] == results[j]["wtag"]:
                assert results[i]["data"] == results[j]["data"]

    for client_id in clients:
        requests.post(f'http://{CLIENT_API}/disconnect', data={'client_id': client_id})

if __name__ == "__main__":
    print("Testing reads after write, reading from local server")
    input("Put all the server up and running and press enter to continue")
    test_reads_after_write(20, True)
    print("-" * 50)
    print("Testing reads after write, reading from remote server")
    input("Put all the server up and running and press enter to continue")
    test_reads_after_write(20, False)
    print("-" * 50)
