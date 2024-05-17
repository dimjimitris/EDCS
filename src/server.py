import socket
import threading as th

import memory_manager as mm
import utils


class Server:
    def __init__(
        self,
        net_address: tuple[str, int],
        memory_ranges: list[tuple[int, int]],
        net_addresses: list[tuple[str, int]],
        dynamic: bool,
    ):
        self.net_address = net_address
        self.memory_ranges = memory_ranges
        self.net_addresses = net_addresses

        # find index of address in addresses
        self.memory_range = memory_ranges[net_addresses.index(net_address)]
        self.memory_manager = mm.MemoryManager(self.memory_range)
        self.shared_manager = {}

        self.connections_to_other_servers: dict[tuple[str, int], socket.socket] = {}
        self.dynamic = dynamic

    def serve_read(self, mem_address, cascade):
        requested_net_address = self._get_net_address(mem_address)

        if requested_net_address == self.net_address:
            self.memory_manager.acquire_lock(mem_address)
            if not cascade:
                self.memory_manager.set_status(mem_address, "S")
            data = self.memory_manager.read(mem_address)
            self.memory_manager.release_lock(mem_address)
            return data

        if mem_address in self.shared_manager:
            self.serve_acquire_lock(mem_address, True)
            data = self.shared_manager[mem_address]
            self.serve_release_lock(mem_address, True)
            return data

        if not cascade:
            return None

        # request from other server
        s = self._connect_to_server(requested_net_address)
        utils.send_msg(s, ("serve_read", mem_address, False))
        data = utils.receive_msg(s)
        self.shared_manager[mem_address] = data
        self._disconnect_from_server(s, requested_net_address)
        return data

    def serve_write(self, mem_address, data, cascade):
        requested_net_address = self._get_net_address(mem_address)

        if requested_net_address == self.net_address:
            self.memory_manager.acquire_lock(mem_address)
            self.memory_manager.write(mem_address, data)
            if not cascade:
                self.memory_manager.set_status(mem_address, "S")
            self.update_shared_copies(mem_address)
            self.memory_manager.release_lock(mem_address)
            return True

        if not cascade:
            return False

        # request from other server
        s = self._connect_to_server(requested_net_address)
        utils.send_msg(s, ("serve_write", mem_address, data, False))
        data = utils.receive_msg(s)
        self._disconnect_from_server(s, requested_net_address)
        return True

    def serve_acquire_lock(self, mem_address, cascade):
        requested_net_address = self._get_net_address(mem_address)

        if requested_net_address == self.net_address:
            self.memory_manager.acquire_lock(mem_address)
            return True

        if not cascade:
            return False

        # request from other server
        s = self._connect_to_server(requested_net_address)
        utils.send_msg(s, ("serve_acquire_lock", mem_address, False))
        data = utils.receive_msg(s)
        self._disconnect_from_server(s, requested_net_address)

        return True

    def serve_release_lock(self, mem_address, cascade):
        requested_net_address = self._get_net_address(mem_address)

        if requested_net_address == self.net_address:
            self.memory_manager.release_lock(mem_address)
            return True

        if not cascade:
            return False

        # request from other server
        s = self._connect_to_server(requested_net_address)
        utils.send_msg(s, ("serve_release_lock", mem_address, False))
        data = utils.receive_msg(s)
        self._disconnect_from_server(s, requested_net_address)

        return True

    def serve_update_shared(self, mem_address, data):
        if mem_address in self.shared_manager:
            self.shared_manager[mem_address] = data

    def update_shared_copies(self, mem_address):
        for net_address in self.net_addresses:
            if net_address == self.net_address:
                continue

            s = self._connect_to_server(net_address)
            utils.send_msg(
                s,
                (
                    "serve_update_shared",
                    mem_address,
                    self.memory_manager.read(mem_address),
                ),
            )
            data = utils.receive_msg(s)
            self.shared_manager[mem_address] = data
            self._disconnect_from_server(s, net_address)

    def handle_client(self, conn: socket.socket, addr: tuple[str, int]):
        print(f"[NEW CONNECTION] {addr} connected.")

        connected = True

        while connected:
            # maybe do the header thing
            msg = utils.receive_msg(conn)
            if msg:
                data = msg

                if data[0] == "disconnect":
                    connected = False
                    data = "disconnecting..."

                if data[0] == "serve_read":
                    data = self.serve_read(data[1], data[2])
                elif data[0] == "serve_write":
                    data = self.serve_write(data[1], data[2], data[3])
                elif data[0] == "serve_acquire_lock":
                    data = self.serve_acquire_lock(data[1], data[2])
                elif data[0] == "serve_release_lock":
                    data = self.serve_release_lock(data[1], data[2])
                elif data[0] == "serve_update_shared":
                    self.serve_update_shared(data[1], data[2])
                    data = True
                print("--------------------")
                print(f"[DATA] {data}")
                print("--------------------")
                utils.send_msg(conn, data)

        print(f"[DISCONNECTED] {addr} disconnected from {self.net_address}.")
        conn.close()

    def serve(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(self.net_address)
            s.listen()
            print(f"[LISTENING] Server is listening on {self.net_address}")
            while True:
                conn, addr = s.accept()
                thread = th.Thread(target=self.handle_client, args=(conn, addr))
                thread.start()
                print(f"[ACTIVE CONNECTIONS] {th.active_count() - 1}")

    def _get_net_address(self, mem_address):
        for idx, memory_range in enumerate(self.memory_ranges):
            if mem_address >= memory_range[0] and mem_address < memory_range[1]:
                return self.net_addresses[idx]

    def _set_up_connections(self):
        if not self.dynamic:
            return False

        for net_address in self.net_addresses:
            if net_address == self.net_address:
                continue
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(net_address)
            self.connections_to_other_servers[net_address] = s
            print(f"server {self.net_address} connected to {net_address}")

    def _connect_to_server(self, requested_net_address):
        # request from other server
        s = None
        if not self.dynamic:
            if requested_net_address in self.connections_to_other_servers:
                s = self.connections_to_other_servers[requested_net_address]
            else:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(requested_net_address)
                self.connections_to_other_servers[requested_net_address] = s
                print(f"server {self.net_address} connected to {requested_net_address}")
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(requested_net_address)
            print(f"server {self.net_address} connected to {requested_net_address}")
        return s

    def _disconnect_from_server(self, s: socket.socket, requested_net_address):
        if self.dynamic:
            utils.send_msg(s, ("disconnect",))
            utils.receive_msg(s)
            s.close()
            print(
                f"server {requested_net_address} disconnected from {self.net_address}"
            )


def start_server_process(
    net_address: tuple[str, int],
    memory_ranges: list[tuple[int, int]],
    net_addresses: list[tuple[str, int]],
    dynamic: bool,
):
    server = Server(net_address, memory_ranges, net_addresses, dynamic)
    server.serve()


memory_ranges = ((0, 100), (100, 200))
net_addresses = [("localhost", 5000), ("localhost", 5001)]


def s1(dynamic=True):
    start_server_process(("localhost", 5000), memory_ranges, net_addresses, dynamic)


def s2(dynamic=True):
    start_server_process(("localhost", 5001), memory_ranges, net_addresses, dynamic)
