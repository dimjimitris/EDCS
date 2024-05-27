import argparse
import socket
import threading as th

import comm_utils as cu
import global_variables as gv


class Client:
    def __init__(self, server_address):
        self.server_address = server_address
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.s.settimeout(3 * gv.CONNECTION_TIMEOUT)
        self.s.connect(self.server_address)

    def disconnect(self):
        cu.send_msg(self.s, {"type": "disconnect"})
        data = cu.rec_msg(self.s)
        self.s.close()
        return data

    def serve_write(self, mem_address, data):
        cu.send_msg(
            self.s,
            {
                "type": "serve_write",
                "args": [
                    "",
                    -1,
                    mem_address,
                    data,
                    True,
                ],
            },
        )
        data = cu.rec_msg(self.s)
        return data

    def serve_read(self, mem_address):
        cu.send_msg(
            self.s,
            {
                "type": "serve_read",
                "args": [
                    "",
                    -1,
                    mem_address,
                    True,
                ],
            },
        )
        data = cu.rec_msg(self.s)
        return data

    def serve_acquire_lock(self, mem_address):
        cu.send_msg(
            self.s,
            {
                "type": "serve_acquire_lock",
                "args": [
                    mem_address,
                    gv.LEASE_TIMEOUT,
                    True,
                ],
            },
        )
        data = cu.rec_msg(self.s)
        return data


def main_cli():
    parser = argparse.ArgumentParser(
        description="CLI program for performing operations on a server."
    )
    parser.add_argument(
        "-server_index", type=int, help="Server index = {0,1,2}", required=True
    )
    parser.add_argument(
        "-operation",
        help="Operation to perform: serve_write, serve_read, serve_acquire_lock",
        required=True,
    )
    parser.add_argument(
        "-address", type=int, help="Memory address to operate on", required=True
    )
    parser.add_argument(
        "-data", help="Data to write (only used in serve_write operation)"
    )

    args = parser.parse_args()

    server_host, server_port = gv.SERVERS[args.server_index % 3]
    server_address = (server_host, int(server_port))

    client = Client(server_address)

    if args.operation == "serve_write":
        if args.data is None:
            print("Data argument is required for serve_write operation")
            return
        result = client.serve_write(args.address, args.data)
    elif args.operation == "serve_read":
        result = client.serve_read(args.address)
    elif args.operation == "serve_acquire_lock":
        result = client.serve_acquire_lock(args.address)
    else:
        print("Invalid operation")
        return

    print(result)

    client.disconnect()


def test():
    i = 0
    while True:
        input_val = int(input("Test number:"))

        if input_val == 1:
            client = Client(gv.SERVERS[0])
            print(client.serve_read(0))
            print(client.disconnect())

        elif input_val == 2:
            client = Client(gv.SERVERS[0])
            print(client.serve_write(0, f"{i}"))
            print(client.disconnect())

        elif input_val == 3:
            client = Client(gv.SERVERS[1])
            print(client.serve_read(100))
            print(client.disconnect())

        elif input_val == 4:
            client = Client(gv.SERVERS[1])
            print(client.serve_write(100, f"{i}"))
            print(client.disconnect())

        elif input_val == 5:
            client = Client(gv.SERVERS[0])
            print(client.serve_read(100))
            print(client.disconnect())

        elif input_val == 6:
            client = Client(gv.SERVERS[0])
            print(client.serve_write(100, f"{i}"))
            print(client.disconnect())

        elif input_val == 7:
            client = Client(gv.SERVERS[1])
            print(client.serve_read(0))
            print(client.disconnect())

        elif input_val == 8:
            client = Client(gv.SERVERS[1])
            print(client.serve_write(0, f"{i}"))
            print(client.disconnect())

        elif input_val == 9:
            thread_cnt = 10
            threads = []

            def client_thread(name):
                client = Client(gv.SERVERS[1])
                print(f"{name}:{client.serve_read(0)}")
                print(client.disconnect())

            def writer_thread(name, num):
                client = Client(gv.SERVERS[0])
                param = f"{num}"
                print(f"{name}:{client.serve_write(0, param)}")
                print(client.disconnect())

            for i in range(thread_cnt):
                threads.append(th.Thread(target=client_thread, args=(i,)))

            threads.append(th.Thread(target=writer_thread, args=(thread_cnt, i)))

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

def test2():
    while True:
        server_index, op, addr, data = input("Give input:").split()
        server_index = int(server_index)
        addr = int(addr)
        client = Client(gv.SERVERS[server_index % 3])
        if op == "read":
            print(client.serve_read(addr))
        elif op == "write":
            print(client.serve_write(addr, data))
        
        print(client.disconnect())


if __name__ == "__main__":
    test2()
