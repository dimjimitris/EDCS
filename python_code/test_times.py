import time
import random
import threading
import client_wrapper as cw
import global_variables as gv
import sys
import jpype

small_data = "test"
large_data = "a" * 1000

def measure_time(func):
    """Decorator to measure the time a function takes to execute."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Time taken by {func.__name__}: {end_time - start_time:.4f} seconds")
        return result
    return wrapper

@measure_time
def test_serial_reads(clients: list[cw.ClientWrapper], mem_address: int, count: int):
    for _ in range(count):
        for client in clients:
            try:
                resp = client.read(mem_address)
                if resp["status"] != gv.SUCCESS:
                    print(f"Failed to read data from server {client.server_address}: {resp}")
            except Exception as e:
                print(f"Failed to read data from server {client.server_address}: {e}")

@measure_time
def test_serial_writes(clients: list[cw.ClientWrapper], mem_address: int, data: str, count: int):
    for _ in range(count):
        for client in clients:
            try:
                resp = client.write(mem_address, data)
                if resp["status"] != gv.SUCCESS:
                    print(f"Failed to write data to server {client.server_address}: {resp}")
            except Exception as e:
                print(f"Failed to write data to server {client.server_address}: {e}")

@measure_time
def test_concurrent_reads(clients: list[cw.ClientWrapper], mem_address: int, count: int):
    def read_operation(client):
        for _ in range(count):
            try:
                resp = client.read(mem_address)
                if resp["status"] != gv.SUCCESS:
                    print(f"Failed to read data from server {client.server_address}: {resp}")
            except Exception as e:
                print(f"Failed to read data from server {client.server_address}: {e}")

    threads = [threading.Thread(target=read_operation, args=(client,)) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

@measure_time
def test_concurrent_writes(clients: list[cw.ClientWrapper], mem_address: int, data: str, count: int):
    def write_operation(client):
        for _ in range(count):
            try:
                resp = client.write(mem_address, data)
                if resp["status"] != gv.SUCCESS:
                    print(f"Failed to write data to server {client.server_address}: {resp}")
            except Exception as e:
                print(f"Failed to write data to server {client.server_address}: {e}")

    threads = [threading.Thread(target=write_operation, args=(client,)) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

@measure_time
def test_random_reads(clients: list[cw.ClientWrapper], count: int):
    for _ in range(count):
        for client in clients:
            mem_address = random.randint(0, gv.MEMORY_SIZE - 1)
            try:
                resp = client.read(mem_address)
                if resp["status"] != gv.SUCCESS:
                    print(f"Failed to read data from server {client.server_address}: {resp}")
            except Exception as e:
                print(f"Failed to read data from server {client.server_address}: {e}")

@measure_time
def test_random_writes(clients: list[cw.ClientWrapper], data: str, count: int):
    for _ in range(count):
        for client in clients:
            mem_address = random.randint(0, gv.MEMORY_SIZE - 1)
            try:
                resp = client.write(mem_address, data)
                if resp["status"] != gv.SUCCESS:
                    print(f"Failed to write data to server {client.server_address}: {resp}")
            except Exception as e:
                print(f"Failed to write data to server {client.server_address}: {e}")

@measure_time
def test_random_concurrent_reads(clients: list[cw.ClientWrapper], count: int):
    def read_operation(client):
        for _ in range(count):
            mem_address = random.randint(0, gv.MEMORY_SIZE - 1)
            try:
                resp = client.read(mem_address)
                if resp["status"] != gv.SUCCESS:
                    print(f"Failed to read data from server {client.server_address}: {resp}")
            except Exception as e:
                print(f"Failed to read data from server {client.server_address}: {e}")

    threads = [threading.Thread(target=read_operation, args=(client,)) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

@measure_time
def test_random_concurrent_writes(clients: list[cw.ClientWrapper], data: str, count: int):
    def write_operation(client):
        for _ in range(count):
            mem_address = random.randint(0, gv.MEMORY_SIZE - 1)
            try:
                resp = client.write(mem_address, data)
                if resp["status"] != gv.SUCCESS:
                    print(f"Failed to write data to server {client.server_address}: {resp}")
            except Exception as e:
                print(f"Failed to write data to server {client.server_address}: {e}")

    threads = [threading.Thread(target=write_operation, args=(client,)) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

# Default client logic type is Python
CLIENT_LOGIC_TYPE = 'python'

if __name__ == "__main__":
    random.seed(17)
    # Check if command-line argument -type is provided and set CLIENT_LOGIC_TYPE accordingly
    if len(sys.argv) > 1 and sys.argv[1] == "-type":
        if len(sys.argv) > 2:
            if sys.argv[2] in ['java', 'python']:
                CLIENT_LOGIC_TYPE = sys.argv[2]
            else:
                print("Invalid client logic type. Please choose 'java' or 'python'.")
                sys.exit(1)
        else:
            print("Client logic type argument missing. Please specify 'java' or 'python'.")
            sys.exit(1)

    # Start the JVM if Java client logic is chosen
    if CLIENT_LOGIC_TYPE == 'java':
        jpype.startJVM(classpath=[gv.JAVA_JAR_FILE])
    
    print("Testing basic functionality")
    input("Put all the server up and running and press enter to continue")
    clients = [
        #cw.ClientWrapper(CLIENT_LOGIC_TYPE, random.choice(gv.SERVERS))
        #for _ in range(2)
        cw.ClientWrapper(CLIENT_LOGIC_TYPE, gv.SERVERS[0]),
        cw.ClientWrapper(CLIENT_LOGIC_TYPE, gv.SERVERS[1])
    ]
    try:
        for client in clients:
            client.connect()
        
        # Test serial and concurrent reads and writes to the same memory address
        mem_address = 0
        count = 1
        small_data = "test"
        large_data = "a" * 1024

        # Testing with small data
        print("-" * 50)
        print("Testing with small data")
        print("-" * 50)
        print("Testing serial reads to the same memory address")
        test_serial_reads(clients, mem_address, count)
        input("Press enter to continue")
        print("Testing serial writes to the same memory address")
        test_serial_writes(clients, mem_address, small_data, count)
        input("Press enter to continue")
        print("Testing concurrent reads to the same memory address")
        test_concurrent_reads(clients, mem_address, count)
        input("Press enter to continue")
        print("Testing concurrent writes to the same memory address")
        test_concurrent_writes(clients, mem_address, small_data, count)
        input("Press enter to continue")
        print("Testing serial reads to random memory addresses")
        test_random_reads(clients, count)
        input("Press enter to continue")
        print("Testing serial writes to random memory addresses")
        test_random_writes(clients, small_data, count)
        input("Press enter to continue")
        print("Testing random concurrent reads")
        test_random_concurrent_reads(clients, count)
        input("Press enter to continue")
        print("Testing random concurrent writes")
        test_random_concurrent_writes(clients, small_data, count)

        # Testing with large data
        print("-" * 50)
        print("Testing with large data")
        print("Testing serial reads to the same memory address")
        print("-" * 50)
        test_serial_reads(clients, mem_address, count)

        print("Testing serial writes to the same memory address")
        test_serial_writes(clients, mem_address, large_data, count)

        print("Testing concurrent reads to the same memory address")
        test_concurrent_reads(clients, mem_address, count)

        print("Testing concurrent writes to the same memory address")
        test_concurrent_writes(clients, mem_address, large_data, count)

        print("Testing serial reads to random memory addresses")
        test_random_reads(clients, count)

        print("Testing serial writes to random memory addresses")
        test_random_writes(clients, large_data, count)

        print("Testing random concurrent reads")
        test_random_concurrent_reads(clients, count)

        print("Testing random concurrent writes")
        test_random_concurrent_writes(clients, large_data, count)
    finally:
        # Disconnect clients
        for client in clients:
            client.disconnect()

    # Stop the JVM if Java client logic is chosen
    if CLIENT_LOGIC_TYPE == 'java':
        jpype.shutdownJVM()
