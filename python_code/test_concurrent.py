import sys

import jpype
import client_wrapper as cw
import time
import threading as th

import global_variables as gv


# Default client logic type
CLIENT_LOGIC_TYPE = 'python'

SERVERS = gv.SERVERS

# all reads after a write return the same data
def test_reads_after_write(thread_cnt, local):
    client = cw.ClientWrapper(CLIENT_LOGIC_TYPE, SERVERS[0])
    client.connect()
    client.write(0, 0)
    client.disconnect()

    local_server = SERVERS[0]
    remote_server = SERVERS[1]

    server = local_server if local else remote_server

    results = [-1 for i in range(thread_cnt - 1)]

    clients = [cw.ClientWrapper(CLIENT_LOGIC_TYPE, server) for _ in range(thread_cnt - 1)]
    clients.append(cw.ClientWrapper(CLIENT_LOGIC_TYPE, local_server))
    for client in clients:
        client.connect()

    def read_thread(idx):
        client : cw.ClientWrapper = clients[idx]
        results[idx] = client.read(0)

    def write_thread(idx):
        client : cw.ClientWrapper = clients[idx]
        client.write(0, 1)

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

if __name__ == "__main__":
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

    print("Testing reads after write, reading from local server")
    input("Put all the server up and running and press enter to continue")
    test_reads_after_write(20, True)
    print("-" * 50)
    print("Testing reads after write, reading from remote server")
    input("Put all the server up and running and press enter to continue")
    test_reads_after_write(20, False)
    print("-" * 50)
    
    if CLIENT_LOGIC_TYPE == 'java':
        jpype.shutdownJVM()