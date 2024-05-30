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

def test_dump_cache(clients : list[cl.Client]):
    for client in clients:
        try:
            resp = client.dump_cache()
            if resp["status"] != gv.SUCCESS:
                print(f"Failed to dump cache from server {client.server_address}: {resp}")
            else:
                print(f"Dump cache from server {client.server_address} with response: {resp}")
        except Exception as e:
            print(f"Failed to dump cache from server {client.server_address}: {e}")

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

def stale_cache():
    client0 = cl.Client(SERVERS[0])
    client1 = cl.Client(SERVERS[1])

    client1.connect()
    resp = client1.write(0, "test")
    print(f"Remote write response: {resp}")

    input("Please restart server 0 and press enter to continue")

    client0.connect()
    resp = client0.write(0, "test2")
    print(f"Local write response: {resp}")
    client0.disconnect()

    resp = client1.dump_cache() # should see stale data
    print(f"Remote dump cache response: {resp}")

    resp = client1.read(0) # cache should be updated
    print(f"Remote read response: {resp}")

    resp = client1.dump_cache() # should see updated data
    print(f"Remote dump cache response: {resp}")

    client1.disconnect()

def corrupted_copy_holder_chain(index):
    if index not in range(1, len(SERVERS)):
        print("Invalid server index, give value 1 or 2")
        return

    clients : list[cl.Client] = []
    for server in SERVERS:
        client = cl.Client(server)
        client.connect()
        clients.append(client)

    resp = clients[0].write(0, "test")
    for client in clients:
        client.read(0)

    if index == 1:
        input("Please turn off server 1 and press enter to continue")
    else:
        input("Please turn off server 2 and press enter to continue")

    resp = clients[0].write(0, "test2")

    if index == 1: # write will not have been propagated to server 2 and server 0 will have memory address 0 as "E" (Exclusive)
        resp = clients[2].dump_cache()
        print(f"Server 2 cache: {resp}")

        resp = clients[0].read(0)
        print(f"Server 0 read response: {resp}")

    else: # write will have been propagated to server 1 and server 0 will have memory address 0 as "S" (Shared)
        resp = clients[1].dump_cache()
        print(f"Server 1 cache: {resp}")

        resp = clients[0].read(0)
        print(f"Server 0 read response: {resp}")

    for client in clients:
        try:
            client.disconnect()
        except Exception as e:
            print(f"Failed to disconnect from server {client.server_address}: {e}")


def test_write_cache():
    client = cl.Client(SERVERS[1])
    client.connect()
    resp = client.write(0, "test")
    print(f"Write response: {resp}")
    resp = client.dump_cache()
    print(f"Dump cache response: {resp}")
    client.disconnect()

def test_read_cache():
    client = cl.Client(SERVERS[1])
    client.connect()
    resp = client.read(0)
    print(f"Read response: {resp}")
    resp = client.dump_cache()
    print(f"Dump cache response: {resp}")
    client.disconnect()

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

