import socket
import threading as th

import global_variables as gv
import memory_manager as mm
import memory_primitives as mp
import comm_utils
import time_utils


CONNECTION_TIMEOUT = gv.CONNECTION_TIMEOUT
LEASE_TIMEOUT = gv.LEASE_TIMEOUT

def log_msg(msg: str, datetime: bool = False):
    print(f"{time_utils.get_datetime() if datetime else ''}{msg}")


class Server:
    def __init__(
        self,
        server_address: tuple[str, int],
        memory_range: tuple[int, int],
        net_addresses: list[tuple[str, int]],
        memory_ranges: list[tuple[int, int]],
    ):
        self.server_address = server_address
        self.memory_range = memory_range
        self.net_addresses = net_addresses
        self.memory_ranges = memory_ranges

        self.memory_manager = mm.MemoryManager(memory_range=self.memory_range)
        self.shared_cache: dict[int, mp.MemoryItem] = {}

    def start(self):
        """
        Description:
        - Start the server and listen for incoming connections from clients

        Return:
        - None
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind(self.server_address)
            server_socket.listen()

            log_msg(f"[LISTENING] Server is listening on {self.server_address}")

            while True:
                client_socket, client_address = server_socket.accept()
                thread = th.Thread(
                    target=self.handle_client, args=(client_socket, client_address)
                )
                thread.start()
                log_msg(f"[ACTIVE CONNECTIONS] Active connections: {th.active_count() - 1}")

    def handle_client(
        self, client_socket: socket.socket, client_address: tuple[str, int]
    ):
        log_msg(f"[NEW CONNECTION] {client_address} connected.")
        connected = True

        while connected:
            return_data = None
            message = None
            try:
                message = comm_utils.receive_message(client_socket)
            except Exception as e:
                log_msg(f"[ERROR RECEIVING] server {self.server_address}, client {client_address}: {e}")
                break

            if not message:
                continue

            args = message.get("args", None)
            if message["type"] == "disconnect":
                connected = False
                return_data = {"status": gv.SUCCESS, "message": "disconnected"}
            elif message["type"] == "serve_read":
                return_data = self.serve_read(client_address, *args)
            elif message["type"] == "serve_write":
                return_data = self.serve_write(client_address, *args)
            elif message["type"] == "serve_acquire_lock":
                return_data = self.serve_acquire_lock(client_address, *args)
            elif message["type"] == "serve_release_lock":
                return_data = self.serve_release_lock(client_address, *args)
            elif message["type"] == "serve_update_cache":
                return_data = self.serve_update_cache(client_address, *args)
            else:
                return_data = {
                    "status": gv.INVALID_OPERATION,
                    "message": "invalid message type",
                }

            try:
                comm_utils.send_message(client_socket, return_data)
            except Exception as e:
                log_msg(f"[ERROR SENDING] server {self.server_address}, client {client_address}: {e}")
                break

        log_msg(f"[DISCONNECTED] server {self.server_address}, client {client_address}.")
        client_socket.close()

    def serve_read(
        self,
        client_address: tuple[str, int],
        copy_holder_ip: str,
        copy_holder_port: int,
        memory_address: int,
        cascade: bool,
        time_out=1,
    ):
        """
        Input:
        - client_address: the address of the client requesting the read
        - copy_holder_ip: the ip address of the server that wants to contain the memory address
        - copy_holder_port: the port of the server that wants to contain the memory address
        - memory_address: the memory address to read from
        - cascade: if True, cascade the request to the server that contains the memory address
        - time_out: if timeout is 0, lock is acquired indefinitely, otherwise, lock is acquired for timeout seconds (only for remote locks)

        Return:
        - response: the response to the read request
        """
        # potentially new holder of the memory address
        copy_holder_address = (copy_holder_ip, copy_holder_port)
        log_msg(f"[READ REQUEST] server {self.server_address}, client {client_address}, address {memory_address}")
        read_host_address_index = self._get_server_index(memory_address)
        if read_host_address_index == -1:
            return {
                "status": gv.INVALID_ADDRESS,
                "message": "Memory address out of range",
            }
        read_host_address = self.net_addresses[read_host_address_index]

        if read_host_address == self.server_address:
            ret_val, counter, tag = self.memory_manager.acquire_lock(memory_address)
            if not ret_val or counter == -1 or tag == -1:
                return {"status": gv.ERROR, "message": "Failed to acquire lock"}
            if not cascade:
                # self.memory_manager.set_status(memory_address, "S")
                self.memory_manager.add_copy_holder(memory_address, copy_holder_address)
            data = self.memory_manager.read_memory(memory_address)
            self.memory_manager.release_lock(memory_address, counter, False)
            data = data.json()
            response = {
                "status": gv.SUCCESS,
                "message": "read successful",
                **data,
            }
            log_msg(f"[READ RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}, response {response}")
            return response

        if memory_address in self.shared_cache:
            ac_lock_val = self.serve_acquire_lock(
                self.server_address, memory_address, time_out, True
            )
            if ac_lock_val["status"] != gv.SUCCESS:
                return ac_lock_val

            if ac_lock_val["tag"] == self.shared_cache[memory_address].tag:
                return_value = self.shared_cache[memory_address].json()
                rel_lock_val = self.serve_release_lock(
                    self.server_address,
                    memory_address,
                    ac_lock_val["counter"],
                    True,
                    True,
                )

                if rel_lock_val["status"] == gv.ERROR:
                    self.shared_cache.pop(memory_address)
                    return {"status": gv.ERROR, "message": "Failed to release lock"}

                if rel_lock_val["tag"] != self.shared_cache[memory_address].tag: # this error might cause issues...
                    # I'm not even sure this error is at all possible
                    self.shared_cache.pop(memory_address)
                    return {"status": gv.ERROR, "message": "Tag mismatch"}

                log_msg(f"[READ RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}, response {return_value}")
                return {
                    "status": gv.SUCCESS,
                    "message": "read successful",
                    **return_value,
                }
            else: # give up and then just communicate with the server
                self.serve_release_lock(
                    self.server_address,
                    memory_address,
                    ac_lock_val["counter"],
                    True,
                    True,
                )

        if not cascade:
            return {
                "status": gv.ERROR,
                "message": f"Read host address {read_host_address} is not the server address {self.server_address}",
            }

        try:
            s = self._connect_to_server(read_host_address)
            comm_utils.send_message(
                s,
                {
                    "type": "serve_read",
                    "args": [self.server_address[0], self.server_address[1], memory_address, False],
                }
            )
            data = comm_utils.receive_message(s)
            self.shared_cache[memory_address] = mp.MemoryItem(
                data["data"], data["istatus"], data["tag"]
            )
            self._disconnect_from_server(s)
            log_msg(f"[READ RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}, response {data}")
            return data
        except Exception as e:
            return {
                "status": gv.ERROR,
                "message": f"Failed to connect to the read host with error: {e}",
            }

    def serve_write(
        self,
        client_address: tuple[str, int],
        copy_holder_ip: str,
        copy_holder_port: int,
        memory_address: int,
        data,
        cascade: bool,
    ):
        """
        Input:
        - client_address: the address of the client requesting the write
        - copy_holder_ip: the ip address of the server that wants to contain the memory address
        - copy_holder_port: the port of the server that wants to contain the memory address
        - memory_address: the memory address to write to
        - data: the data to write
        - cascade: if True, cascade the request to the server that contains the memory address

        Return:
        - response: the response to the write request
        """
        copy_holder_address = (copy_holder_ip, copy_holder_port)
        log_msg(f"[WRITE REQUEST] server {self.server_address}, client {client_address}, address {memory_address}")
        write_host_address_index = self._get_server_index(memory_address)
        if write_host_address_index == -1:
            return {"status": gv.ERROR, "message": "Memory address out of range"}
        write_host_address = self.net_addresses[write_host_address_index]

        if write_host_address == self.server_address:
            ret_val, counter, tag = self.memory_manager.acquire_lock(
                memory_address
            )
            if not ret_val or counter == -1 or tag == -1:
                return {"status": gv.ERROR, "message": "Failed to acquire lock"}
            prev_status = self.memory_manager.read_memory(memory_address).status
            if not cascade:
                #self.memory_manager.set_status(memory_address, "S")
                self.memory_manager.add_copy_holder(
                    memory_address, copy_holder_address
                )
            self.memory_manager.write_memory(memory_address, data)
            # update shared copies in the system, if they exist!
            if prev_status == "S":
                self._update_shared_copies(client_address, memory_address)

            self.memory_manager.release_lock(memory_address, counter, False)
            response = {
                "status": gv.SUCCESS,
                "message": "write successful",
            }
            log_msg(f"[WRITE RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}, response {response}")
            return response

        if not cascade:
            return {
                "status": gv.ERROR,
                "message": f"Write host address {write_host_address} is not the server address {self.server_address}",
            }

        try:
            s = self._connect_to_server(write_host_address)
            comm_utils.send_message(
                s,
                {
                    "type": "serve_write",
                    "args": [self.server_address[0], self.server_address[1], memory_address, data, False],
                },
            )
            response = comm_utils.receive_message(s)
            self._disconnect_from_server(s)
            log_msg(f"[WRITE RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}, response {response}")
            return response
        except Exception as e:
            return {
                "status": gv.ERROR,
                "message": f"Failed to connect to the write host with error: {e}",
            }

    def serve_acquire_lock(
        self,
        client_address: tuple[str, int],
        memory_address: int,
        lease_timout: int,
        cascade: bool,
    ):
        """
        Input:
        - client_address: the address of the client requesting the lock
        - memory_address: the memory address to acquire the lock for
        - timeout: if timeout is 0, lock is acquired indefinitely, otherwise, lock is acquired for timeout seconds
        - cascade: if True, cascade the request to the server that contains the memory address

        Return:
        - response: the response to the acquire lock request
        """
        log_msg(f"[ACQUIRE LOCK REQUEST] server {self.server_address}, client {client_address}, memory address {memory_address}")
        host_server_index = self._get_server_index(memory_address)
        if host_server_index == -1:
            return {
                "status": gv.INVALID_ADDRESS,
                "message": "memory address out of range",
            }
        host_server_address = self.net_addresses[host_server_index]

        if host_server_address == self.server_address:
            ret_val, counter, tag = self.memory_manager.acquire_lock(
                memory_address, lease_timout
            )

            response = None
            if ret_val:
                response = {
                    "status": gv.SUCCESS,
                    "message": "lock acquired",
                    "ret_val": ret_val,
                    "counter": counter,
                    "tag": tag,
                }
            else:
                response = {"status": gv.ERROR, "message": "lock not acquired"}
            log_msg(f"[ACQUIRE LOCK RESPONSE] server {self.server_address}, client {client_address}, memory address {memory_address}, response {response}")
            return response

        if not cascade:
            return {
                "status": gv.ERROR,
                "message": f"Lock host address {host_server_address} is not the server address {self.server_address}",
            }

        try:
            host_server_socket = self._connect_to_server(
                host_server_address, CONNECTION_TIMEOUT
            )
            comm_utils.send_message(
                host_server_socket,
                {
                    "type": "serve_acquire_lock",
                    "args": [memory_address, lease_timout, False],
                },
            )
            response = comm_utils.receive_message(host_server_socket)
            self._disconnect_from_server(host_server_socket)
            log_msg(f"[ACQUIRE LOCK RESPONSE] server {self.server_address}, client {client_address}, memory address {memory_address}, response {response}")
            return response
        except Exception as e:
            log_msg(f"[ERROR ACQUIRING LOCK] server {self.server_address}, client {client_address}, memory address {memory_address}: {e}")
            return {
                "status": gv.ERROR,
                "message": f"Failed to connect to the lock host with error: {e}",
            }

    def serve_release_lock(
        self,
        client_address: tuple[str, int],
        memory_address: int,
        lease_counter: int,
        increment_counter: bool,
        cascade: bool,
    ):
        """
        Input:
        - client_address: the address of the client requesting the lock release
        - memory_address: the memory address to release the lock for
        - lease_counter: the counter of the lock when it was acquired
        - increment_counter: if True, increment the counter by 1
        - cascade: if True, cascade the request to the server that contains the memory address
        """
        log_msg(f"[RELEASE LOCK REQUEST] server {self.server_address}, client {client_address}, address {memory_address}")
        lock_host_address_index = self._get_server_index(memory_address)
        if lock_host_address_index == -1:
            return {
                "status": gv.INVALID_ADDRESS,
                "message": "Memory address out of range",
            }
        lock_host_address = self.net_addresses[lock_host_address_index]

        if lock_host_address == self.server_address:
            ret_val, counter, tag = self.memory_manager.release_lock(
                memory_address, lease_counter, increment_counter
            )
            response = None
            if ret_val:
                response = {
                    "status": gv.SUCCESS,
                    "message": "lock released",
                    "ret_val": ret_val,
                    "counter": counter,
                    "tag": tag,
                }
            else:
                response = {
                    "status": gv.SUCCESS,
                    "message": "lock was already released",
                    "ret_val": ret_val,
                    "counter": counter,
                    "tag": tag,
                }
            log_msg(f"[RELEASE LOCK RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}, response {response}")
            return response

        if not cascade:
            return {
                "status": gv.ERROR,
                "message": f"Lock host address {lock_host_address} is not the server address {self.server_address}",
            }
        try:
            s = self._connect_to_server(lock_host_address)
            comm_utils.send_message(
                s,
                {
                    "type": "serve_release_lock",
                    "args": [memory_address, lease_counter, increment_counter, False],
                },
            )
            response = comm_utils.receive_message(s)
            self._disconnect_from_server(s)
            log_msg(f"[RELEASE LOCK RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}, response {response}")
            return response
        except Exception as e:
            return {
                "status": gv.ERROR,
                "message": f"Failed to connect to the lock host with error: {e}",
            }

    def serve_update_cache(
        self,
        client_address: tuple[str, int],
        memory_address: int,
        data,
        istatus,
        tag,
    ):
        """
        Input:
        - client_address: the address of the client requesting the cache update
        - memory_address: the memory address to update the cache for
        - data: the data to update the cache with
        - istatus: the status of the memory item
        - tag: the tag of the memory item

        Return:
        - response: the response to the cache update request
        """
        log_msg(f"[UPDATE CACHE REQUEST] server {self.server_address}, client {client_address}, address {memory_address}")
        if memory_address in self.shared_cache:
            self.shared_cache[memory_address] = mp.MemoryItem(data, istatus, tag)
        log_msg(f"[UPDATE CACHE RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}")
        return {"status": gv.SUCCESS, "message": "cache updated"}

    def _get_server_index(self, memory_address: int) -> int:
        """
        Input:
        - memory_address: the memory address to get the server index for

        Return:
        - server_index: the index of the server that contains the memory address, -1 if the memory address is out of range
        """
        for i, memory_range in enumerate(self.memory_ranges):
            if memory_address in range(memory_range[0], memory_range[1]):
                return i
        return -1

    def _connect_to_server(
        self, server_address: tuple[str, int], timeout=None
    ) -> socket.socket:
        """
        Input:
        - server_address: the address of the server to connect to
        - timeout: the timeout for the connection in seconds (float)

        Return:
        - server_socket: the socket connected to the server
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.settimeout(timeout)  # timeout only used for connection
        server_socket.connect(server_address)
        # server_socket.settimeout(None) # remove timeout after connection
        return server_socket

    def _disconnect_from_server(self, server_socket: socket.socket):
        """
        Input:
        - server_socket: the socket to disconnect from

        Return:
        - None
        """
        try:
            comm_utils.send_message(server_socket, {"type": "disconnect"})
            comm_utils.receive_message(server_socket)
        finally:
            server_socket.close()

    def _update_shared_copy(
        self,
        client_address: tuple[str, int],
        memory_address: int,
        target_address: tuple[str, int],
    ):
        log_msg(f"[UPDATE SINGLE CACHE REQUEST] server {self.server_address}, client {client_address}, address {memory_address}, target {target_address}")
        try:
            s = self._connect_to_server(target_address)
            comm_utils.send_message(
                s,
                {
                    "type": "serve_update_cache",
                    "args": [
                        memory_address,
                        self.memory_manager.read_memory(memory_address).data,
                        self.memory_manager.read_memory(memory_address).status,
                        self.memory_manager.read_memory(memory_address).tag,
                    ],
                },
            )
            comm_utils.receive_message(s)
            self._disconnect_from_server(s)
            log_msg(f"[UPDATE SINGLE CACHE RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}, target {target_address}")
            return {"status": gv.SUCCESS, "message": "cache updated"}
        except Exception as e:
            self.memory_manager.remove_copy_holder(memory_address, target_address)
            return {
                "status": gv.ERROR,
                "message": f"Failed to connect to the target address with error: {e}",
            }

    def _update_shared_copies(
        self,
        client_address: tuple[str, int],
        memory_address: int,
    ):
        log_msg(f"[UPDATE ALL CACHE REQUEST] server {self.server_address}, client {client_address}, address {memory_address}")

        threads = [
            th.Thread(
                target=self._update_shared_copy,
                args=(client_address, memory_address, target_address),
            )
            for target_address in self.memory_manager.get_copy_holders(memory_address)
            if target_address != self.server_address
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        log_msg(f"[UPDATE ALL CACHE RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}")
        return {"status": gv.SUCCESS, "message": "cache updated"}

# just for testing purposes...
def start_server_process(
    net_address: tuple[str, int],
    memory_range: tuple[int, int],
    net_addresses: list[tuple[str, int]],
    memory_ranges: list[tuple[int, int]],
):
    server = Server(net_address, memory_range, net_addresses, memory_ranges)
    server.start()


memory_ranges = ((0, 100), (100, 200))
net_addresses = [("localhost", 5000), ("localhost", 5001)]


def s1(dynamic=True):
    start_server_process(("localhost", 5000), (0, 100), net_addresses, memory_ranges)


def s2(dynamic=True):
    start_server_process(("localhost", 5001), (100, 200), net_addresses, memory_ranges)