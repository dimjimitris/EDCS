import client_logic as cl
import global_variables as gv

SERVERS = gv.SERVERS

def test_connect():
    clients = []
    for server in SERVERS:
        client = cl.Client(server)
        try :
            client.connect()
            clients.append(client)
        except Exception as e:
            print(f"Failed to connect to server {server}: {e}")
    return clients

def test_disconnect(clients : list[cl.Client]):
    for client in clients:
        try:
            resp = client.disconnect()
            if resp["status"] != gv.SUCCESS:
                print(f"Failed to disconnect from server {client.server_address}: {resp}")
            else:
                print(f"Disconnected from server {client.server_address} with response: {resp}")
        except Exception as e:
            print(f"Failed to disconnect from server {client.server_address}: {e}")

def test_write(clients : list[cl.Client], local):
    server_memory_size = gv.MEMORY_SIZE // len(SERVERS)
    for idx, client in enumerate(clients):
        index = idx if local else (idx + 1) % len(SERVERS)
        mem_address = index * server_memory_size
        data = "test"
        try:
            resp = client.write(mem_address, data)
            if resp["status"] != gv.SUCCESS:
                print(f"Failed to write data to server {client.server_address}: {resp}")
            else:
                print(f"Write data to server {client.server_address} with response: {resp}")
        except Exception as e:
            print(f"Failed to write data to server {client.server_address}: {e}")

def test_read(clients : list[cl.Client], local):
    server_memory_size = gv.MEMORY_SIZE // len(SERVERS)
    for idx, client in enumerate(clients):
        index = idx if local else (idx + 1) % len(SERVERS)
        mem_address = index * server_memory_size
        try:
            resp = client.read(mem_address)
            if resp["status"] != gv.SUCCESS or (not local and resp["istatus"] != "S"):
                print(f"Failed to read data from server {client.server_address}: {resp}")
            else:
                print(f"Read data from server {client.server_address} with response: {resp}")
        except Exception as e:
            print(f"Failed to read data from server {client.server_address}: {e}")

def test_acquire_and_release_lock(clients : list[cl.Client], local):
    server_memory_size = gv.MEMORY_SIZE // len(SERVERS)
    for idx, client in enumerate(clients):
        index = idx if local else (idx + 1) % len(SERVERS)
        mem_address = index * server_memory_size
        try:
            resp = client.acquire_lock(mem_address)
            if resp["status"] != gv.SUCCESS:
                print(f"Failed to acquire lock from server {client.server_address}: {resp}")
            else:
                print(f"Acquire lock from server {client.server_address} with response: {resp}")
        except Exception as e:
            print(f"Failed to acquire lock from server {client.server_address}: {e}")
        try:
            if resp is not None and resp["status"] == gv.SUCCESS:
                resp = client.release_lock(mem_address, resp["ltag"])
                if resp["status"] != gv.SUCCESS:
                    print(f"Failed to release lock from server {client.server_address}: {resp}")
                else:
                    print(f"Release lock from server {client.server_address} with response: {resp}")
        except Exception as e:
            print(f"Failed to release lock from server {client.server_address}: {e}")

def test():
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
    print("Testing remote read")
    test_read(clients, False)
    print("-" * 50)
    print("Testing remote acquire and release lock")
    test_acquire_and_release_lock(clients, False)
    print("-" * 50)
    print("Testing disconnect")
    test_disconnect(clients)

if __name__ == "__main__":
    test()