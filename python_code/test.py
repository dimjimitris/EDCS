import requests

import global_variables as gv

SERVERS = gv.SERVERS
CLIENT_API = gv.CLIENT_API

def test_connect():
    clients = []
    for server_index in range(len(SERVERS)):
        client = server_index
        try :
            resp = requests.post(f'http://{CLIENT_API}/connect', data={'client_id': client, 'server_index': server_index})
            clients.append(client)
            print(resp.json()["response"])
        except Exception as e:
            print(f"Failed to connect to server {SERVERS[server_index]}: {e}")
    return clients

def test_disconnect(clients : list[int]):
    for client_id, server_index in enumerate(clients):
        try:
            resp = requests.post(f'http://{CLIENT_API}/disconnect', data={'client_id': client_id})
            resp = resp.json()["response"]
            if resp["status"] != gv.SUCCESS:
                print(f"Failed to disconnect from server {SERVERS[server_index]}: {resp}")
            else:
                print(f"Disconnected from server {SERVERS[server_index]} with response: {resp}")
        except Exception as e:
            print(f"Failed to disconnect from server {SERVERS[server_index]}: {e}")

def test_write(clients : list[int], local):
    server_memory_size = gv.MEMORY_SIZE // len(SERVERS)
    for client_id, server_index in enumerate(clients):
        index = client_id if local else (client_id + 1) % len(SERVERS)
        mem_address = index * server_memory_size
        data = "test"
        try:
            resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client_id, 'command': 'write', 'mem_address': mem_address, 'data': data})
            resp = resp.json()["response"]
            if resp["status"] != gv.SUCCESS:
                print(f"Failed to write data to server {SERVERS[server_index]}: {resp}")
            else:
                print(f"Write data to server {SERVERS[server_index]} with response: {resp}")
        except Exception as e:
            print(f"Failed to write data to server {SERVERS[server_index]}: {e}")

def test_dump_cache(clients : list[int]):
    for client_id, server_index in enumerate(clients):
        try:
            resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client_id, 'command': 'dumpcache'})
            resp = resp.json()["response"]
            if resp["status"] != gv.SUCCESS:
                print(f"Failed to dump cache from server {SERVERS[server_index]}: {resp}")
            else:
                print(f"Dump cache from server {SERVERS[server_index]} with response: {resp}")
        except Exception as e:
            print(f"Failed to dump cache from server {SERVERS[server_index]}: {e}")

def test_read(clients : list[int], local):
    server_memory_size = gv.MEMORY_SIZE // len(SERVERS)
    for client_id, server_index in enumerate(clients):
        index = client_id if local else (client_id + 1) % len(SERVERS)
        mem_address = index * server_memory_size
        try:
            resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client_id, 'command': 'read', 'mem_address': mem_address})
            resp = resp.json()["response"]
            if resp["status"] != gv.SUCCESS or (not local and resp["istatus"] != "S"):
                print(f"Failed to read data from server {SERVERS[server_index]}: {resp}")
            else:
                print(f"Read data from server {SERVERS[server_index]} with response: {resp}")
        except Exception as e:
            print(f"Failed to read data from server {SERVERS[server_index]}: {e}")

def test_acquire_and_release_lock(clients : list[int], local):
    server_memory_size = gv.MEMORY_SIZE // len(SERVERS)
    for client_id, server_index in enumerate(clients):
        index = client_id if local else (client_id + 1) % len(SERVERS)
        mem_address = index * server_memory_size
        try:
            resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client_id, 'command': 'lock', 'mem_address': mem_address})
            resp = resp.json()["response"]
            if resp["status"] != gv.SUCCESS:
                print(f"Failed to acquire lock from server {SERVERS[server_index]}: {resp}")
            else:
                print(f"Acquire lock from server {SERVERS[server_index]} with response: {resp}")
        except Exception as e:
            print(f"Failed to acquire lock from server {SERVERS[server_index]}: {e}")
        try:
            if resp is not None and resp["status"] == gv.SUCCESS:
                resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client_id, 'command': 'unlock', 'mem_address': mem_address, 'lease_tag': resp["ltag"]})
                resp = resp.json()["response"]
                if resp["status"] != gv.SUCCESS:
                    print(f"Failed to release lock from server {SERVERS[server_index]}: {resp}")
                else:
                    print(f"Release lock from server {SERVERS[server_index]} with response: {resp}")
        except Exception as e:
            print(f"Failed to release lock from server {SERVERS[server_index]}: {e}")

def stale_cache():
    client0 = 0
    client1 = 1

    requests.post(f'http://{CLIENT_API}/connect', data={'client_id': client1, 'server_index': client1})
    resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client1, 'command': 'write', 'mem_address': 0, 'data': "test"})
    resp = resp.json()["response"]
    print(f"Remote write response: {resp}")

    input("Please restart server 0 and press enter to continue")

    requests.post(f'http://{CLIENT_API}/connect', data={'client_id': client0, 'server_index': client0})
    resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client0, 'command': 'write', 'mem_address': 0, 'data': "test2"})
    resp = resp.json()["response"]
    print(f"Local write response: {resp}")
    requests.post(f'http://{CLIENT_API}/disconnect', data={'client_id': client0})

    resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client1, 'command': 'dumpcache'})
    resp = resp.json()["response"]
    # should see stale data
    print(f"Remote dump cache response: {resp}")

    resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client1, 'command': 'read', 'mem_address': 0})
    resp = resp.json()["response"]
    # should see updated data
    print(f"Remote read response: {resp}")

    resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client1, 'command': 'dumpcache'})
    resp = resp.json()["response"]
    # should see updated data
    print(f"Remote dump cache response: {resp}")

    requests.post(f'http://{CLIENT_API}/disconnect', data={'client_id': client1})

def corrupted_copy_holder_chain(index):
    if index not in range(1, len(SERVERS)):
        print("Invalid server index, give value 1 or 2")
        return

    clients : list[int] = []
    for server_index in range(len(SERVERS)):
        client = server_index
        requests.post(f'http://{CLIENT_API}/connect', data={'client_id': client, 'server_index': server_index})
        clients.append(client)

    resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': clients[0],  'command': 'write', 'mem_address': 0, 'data': "test"})
    for client in clients:
        requests.post(f'http://{CLIENT_API}/command', data={'client_id': client,  'command': 'read', 'mem_address': 0})

    if index == 1:
        input("Please turn off server 1 and press enter to continue")
    else:
        input("Please turn off server 2 and press enter to continue")

    resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': clients[0],  'command': 'write', 'mem_address': 0, 'data': "test2"})
    resp = resp.json()["response"]

    if index == 1: # write will not have been propagated to server 2 and server 0 will have memory address 0 as "E" (Exclusive)
        resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': clients[2], 'command': 'dumpcache',})
        resp = resp.json()["response"]
        print(f"Server 2 cache: {resp}")

        resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': clients[0],  'command': 'read', 'mem_address': 0})
        resp = resp.json()["response"]
        print(f"Server 0 read response: {resp}")

    else: # write will have been propagated to server 1 and server 0 will have memory address 0 as "S" (Shared)
        resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': clients[1], 'command': 'dumpcache', })
        resp = resp.json()["response"]
        print(f"Server 1 cache: {resp}")

        resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': clients[0],  'command': 'read', 'mem_address': 0})
        resp = resp.json()["response"]
        print(f"Server 0 read response: {resp}")

    for client in clients:
        try:
            requests.post(f'http://{CLIENT_API}/disconnect', data={'client_id': client})
        except Exception as e:
            print(f"Failed to disconnect from server {SERVERS[client]}: {e}")


def test_write_cache():
    client = 1
    requests.post(f'http://{CLIENT_API}/connect', data={'client_id': client, 'server_index': client})
    resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client, 'command': 'write', 'mem_address': 0, 'data': "test"})
    try:
        resp = resp.json()["response"]
    except:
        print(ascii(resp))
    print(f"Write response: {resp}")
    resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client, 'command': 'dumpcache'})
    resp = resp.json()["response"]
    print(f"Dump cache response: {resp}")
    requests.post(f'http://{CLIENT_API}/disconnect', data={'client_id': client})

def test_read_cache():
    client = 1
    requests.post(f'http://{CLIENT_API}/connect', data={'client_id': client, 'server_index': client})
    resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client, 'command': 'read', 'mem_address': 0})
    resp = resp.json()["response"]
    print(f"Read response: {resp}")
    resp = requests.post(f'http://{CLIENT_API}/command', data={'client_id': client, 'command': 'dumpcache'})
    resp = resp.json()["response"]
    print(f"Dump cache response: {resp}")
    requests.post(f'http://{CLIENT_API}/disconnect', data={'client_id': client})

def test_basic():
    print("-" * 50)
    print("Testing connect")
    clients = test_connect()
    print("-" * 50)
    print("Testing local write")
    test_write(clients, True)
    print("-" * 50)
    print("Testing local read")
    test_read(clients, True)
    print("-" * 50)
    print("Testing local acquire and release lock")
    test_acquire_and_release_lock(clients, True)
    print("-" * 50)
    print("Testing remote write")
    test_write(clients, False)
    print("-" * 50)
    print("Testing dump cache")
    test_dump_cache(clients)
    print("-" * 50)
    print("Testing local read again")
    test_read(clients, True)
    print("-" * 50)
    print("Testing remote read")
    test_read(clients, False)
    print("-" * 50)
    print("Testing remote acquire and release lock")
    test_acquire_and_release_lock(clients, False)
    print("-" * 50)
    print("Testing disconnect")
    test_disconnect(clients)
    print("-" * 50)

def test_cache():
    print("Testing sleeping cache")
    stale_cache()
    print("-" * 50)
    
def test_copy_holder_chain(index):
    print(f"Testing corrupted copy holder chain with server {index} down")
    corrupted_copy_holder_chain(index)
    print("-" * 50)

if __name__ == "__main__":
    print("Testing basic functionality")
    input("Put all the server up and running and press enter to continue")
    test_basic()
    print("Testing write cache")
    input("Put all the server up and running and press enter to continue")
    test_write_cache()
    print("Testing read cache")
    input("Put all the server up and running and press enter to continue")
    test_read_cache()
    print("Testing cache")
    input("Put all the server up and running and press enter to continue")
    test_cache()
    print("Testing copy holder chain with middle server down")
    input("Put all the server up and running and press enter to continue")
    test_copy_holder_chain(1)
    print("Testing copy holder chain with last server down")
    input("Put all the server up and running and press enter to continue")
    test_copy_holder_chain(2)

