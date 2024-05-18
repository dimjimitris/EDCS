import utils
import socket
import threading
import random

class Client:
    def __init__(
        self,
        server_address,
    ):
        self.server_address = server_address

    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect(self.server_address)

    def disconnect(self):
        utils.send_msg(self.s, ("disconnect",))
        data = utils.receive_msg(self.s)
        self.s.close()
        return data

    def write(self, mem_address, data):
        utils.send_msg(self.s, ("serve_write", mem_address, data, True))
        data = utils.receive_msg(self.s)
        return data

    def read(self, mem_address):
        utils.send_msg(self.s, ("serve_read", mem_address, True))
        data = utils.receive_msg(self.s)
        return data


def main():
    client_5000 = Client(("localhost", 5000))
    client_5001 = Client(("localhost", 5001))

    i = 42
    while True:
        i = i + 1
        action = str(input("Enter action: "))

        if action == "exit":
            break

        if action == "1":
            client_5000.connect()
            client_5000.write(0, "hello")
            print(client_5000.read(0))
            client_5000.disconnect()

        if action == "2":
            client_5001.connect()
            client_5001.write(100, "world")
            print(client_5001.read(100))
            client_5001.disconnect()

        if action == "3":
            client_5000.connect()
            client_5001.connect()
            print(client_5000.read(100))
            client_5000.write(100, f"{i}")
            print(client_5001.read(100))
            client_5000.disconnect()
            client_5001.disconnect()

        if action == "4":
            client_5000.connect()
            client_5001.connect()
            print(client_5000.read(100))
            client_5000.write(100, "everything")
            print(client_5001.read(100))
            client_5000.disconnect()
            client_5001.disconnect()

        if action == "5":
            tries = 10

            def reader(num, client: Client):
                client.connect()
                print(f"thread {num} connected")
                for _ in range(1):
                    print(f"{num:02d}: {client.read(100)}")
                client.disconnect()

            def writer(num, write_num, client: Client):
                client.connect()
                print(f"thread {num} connected")
                for _ in range(1):
                    print(f"{num:02d}: {client.write(100, f"{write_num}_opium")}")
                client.disconnect()

            threads = [
                threading.Thread(target=reader, args=(idx, Client(("localhost", 5001))))
                for idx in range(tries)
            ]
            threads.append(threading.Thread(target=writer, args=(tries, i, Client(("localhost", 5001)))))

            #random.shuffle(threads)

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        if action == "6":
            client_5001.connect()
            print(client_5001.read(100))
            client_5001.disconnect()

if __name__ == "__main__":
    main()
