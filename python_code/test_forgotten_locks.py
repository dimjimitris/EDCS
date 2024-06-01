import client_wrapper as cw
import global_variables as gv
import time
import threading as th
import sys
import jpype

sleep_time = (gv.LEASE_TIMEOUT + 1) // 2

# Default client logic type
CLIENT_LOGIC_TYPE = 'python'

def test_forgotten_locks():
    def acquire_lock_thread():
        client = cw.ClientWrapper(CLIENT_LOGIC_TYPE, gv.SERVERS[0])
        client.connect()
        resp = client.acquire_lock(0)
        print(f"Acquire lock response: {resp}")
        client.disconnect()

    def re_acquire_lock_thread():
        time.sleep(sleep_time)
        client = cw.ClientWrapper(CLIENT_LOGIC_TYPE, gv.SERVERS[0])
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

    test_forgotten_locks()

    # Stop the JVM if Java client logic is chosen
    if CLIENT_LOGIC_TYPE == 'java':
        jpype.shutdownJVM()