import client_wrapper as cw
import global_variables as gv
import time
import threading as th
import jpype
import argparse

sleep_time = (gv.LEASE_TIMEOUT + 1) // 2

# Default client logic type
CLIENT_LOGIC_TYPE = 'python'

def test_forgotten_locks(server_index):
    """
    Description: test that forgotten locks are released after the lease timeout
    """
    memory_address = (gv.MEMORY_SIZE // len(gv.SERVERS)) * server_index
    def acquire_lock_thread():
        client = cw.ClientWrapper(CLIENT_LOGIC_TYPE, gv.SERVERS[server_index])
        client.connect()
        resp = client.acquire_lock(memory_address)
        print(f"Acquire lock response: {resp}")
        client.disconnect()

    def re_acquire_lock_thread():
        time.sleep(sleep_time)
        client = cw.ClientWrapper(CLIENT_LOGIC_TYPE, gv.SERVERS[server_index])
        client.connect()
        resp = client.acquire_lock(memory_address)
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


CLIENT_LOGIC_TYPE = 'python'
SERVER_INDEX = 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-type", choices=['java', 'python'], default='python')
    parser.add_argument("-server", type=int, default=0)
    args = parser.parse_args()

    CLIENT_LOGIC_TYPE = args.type
    SERVER_INDEX = args.server

    # Start the JVM if Java client logic is chosen
    if CLIENT_LOGIC_TYPE == 'java':
        jpype.startJVM(classpath=[gv.JAVA_JAR_FILE])

    test_forgotten_locks(SERVER_INDEX)

    # Stop the JVM if Java client logic is chosen
    if CLIENT_LOGIC_TYPE == 'java':
        jpype.shutdownJVM()