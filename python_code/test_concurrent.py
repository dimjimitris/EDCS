import sys

import jpype
import client_wrapper as cw
import argparse
import threading as th

import global_variables as gv

SERVERS = gv.SERVERS

# all reads after a write return the same data
def test_reads_after_write(server_index, thread_cnt, local):
    """
    Description: Consistency test, all reads after a write should return the same data
    """
    client = cw.ClientWrapper(CLIENT_LOGIC_TYPE, SERVERS[server_index])

    memory_address = server_index * (gv.MEMORY_SIZE // len(SERVERS))

    client.connect()
    client.write(memory_address, 0)
    client.disconnect()

    local_server = SERVERS[server_index]
    remote_server = SERVERS[(server_index + 1) % len(SERVERS)]

    server = local_server if local else remote_server

    results = [-1 for i in range(thread_cnt - 1)]

    clients = [cw.ClientWrapper(CLIENT_LOGIC_TYPE, server) for _ in range(thread_cnt - 1)]
    clients.append(cw.ClientWrapper(CLIENT_LOGIC_TYPE, local_server))
    for client in clients:
        client.connect()

    def read_thread(idx):
        client : cw.ClientWrapper = clients[idx]
        results[idx] = client.read(memory_address)

    def write_thread(idx):
        client : cw.ClientWrapper = clients[idx]
        client.write(memory_address, 1)

    threads = [th.Thread(target=read_thread, args=(i,)) for i in range(thread_cnt - 1)]
    threads.append(th.Thread(target=write_thread, args=(thread_cnt - 1,)))

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    for i in range(thread_cnt - 1):
        for j in range(thread_cnt - 1):
            if results[i]["wtag"] > results[j]["wtag"]:
                assert results[i]["data"] > results[j]["data"]
            if results[i]["wtag"] == results[j]["wtag"]:
                assert results[i]["data"] == results[j]["data"]

    for client in clients:
        client.disconnect()

# Default client logic type
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

    print("Testing reads after write, reading from local server")
    input("Put all the server up and running and press enter to continue")
    test_reads_after_write(SERVER_INDEX, 20, True)
    print("-" * 50)
    print("Testing reads after write, reading from remote server")
    input("Put all the server up and running and press enter to continue")
    test_reads_after_write(SERVER_INDEX, 20, False)
    print("-" * 50)
    
    if CLIENT_LOGIC_TYPE == 'java':
        jpype.shutdownJVM()