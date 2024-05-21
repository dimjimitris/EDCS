import argparse
import socket

import comm_utils
import global_variables as gv

class Client:
    def __init__(self, server_address):
        self.server_address = server_address
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect(self.server_address)

    def disconnect(self):
        comm_utils.send_message(self.s, {"type": "disconnect"})
        data = comm_utils.receive_message(self.s)
        self.s.close()
        return data

    def serve_write(self, mem_address, data):
        comm_utils.send_message(self.s, {
            "type": "serve_write",
            "args": [
                "", -1, mem_address, data, True,
            ]
        })
        data = comm_utils.receive_message(self.s)
        return data

    def serve_read(self, mem_address):
        comm_utils.send_message(self.s, {
            "type": "serve_read",
            "args": [
                "", -1, mem_address, True,
            ]
        })
        data = comm_utils.receive_message(self.s)
        return data

    def serve_acquire_lock(self, mem_address):
        comm_utils.send_message(self.s, {
            "type": "serve_acquire_lock",
            "args": [
                mem_address, gv.LEASE_TIMEOUT, True,
            ]
        })
        data = comm_utils.receive_message(self.s)
        return data

def main_cli():
    parser = argparse.ArgumentParser(description='CLI program for performing operations on a server.')
    parser.add_argument('-server', help='Server address in the format "host:port"', required=True)
    parser.add_argument('-operation', help='Operation to perform: serve_write, serve_read, serve_acquire_lock', required=True)
    parser.add_argument('-address', help='Memory address to operate on', required=True)
    parser.add_argument('-data', help='Data to write (only used in serve_write operation)')

    args = parser.parse_args()

    server_host, server_port = args.server.split(':')
    server_address = (server_host, int(server_port))

    client = Client(server_address)
    args.address = int(args.address)

    if args.operation == 'serve_write':
        if args.data is None:
            print('Data argument is required for serve_write operation')
            return
        result = client.serve_write(args.address, args.data)
    elif args.operation == 'serve_read':
        result = client.serve_read(args.address)
    elif args.operation == 'serve_acquire_lock':
        result = client.serve_acquire_lock(args.address)
    elif args.operation == 'serve_release_lock':
        result = client.serve_release_lock(args.address)
    else:
        print('Invalid operation')
        return

    print(result)

    client.disconnect()

if __name__ == "__main__":
    main_cli()
