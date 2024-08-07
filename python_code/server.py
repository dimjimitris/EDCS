import socket
import threading as th

import global_variables as gv
import memory_manager as mm
import memory_primitives as mp
import cache
import comm_utils as cu
import time_utils as tu

CONNECTION_TIMEOUT = gv.CONNECTION_TIMEOUT
LEASE_TIMEOUT = gv.LEASE_TIMEOUT
CACHE_SIZE = gv.CACHE_SIZE


# simple logging function which adds (or not) a timestamp at the
# start of the message
def log_msg(msg: str, datetime: bool = False):
    print(f"{tu.get_datetime() if datetime else ''}{msg}")


class Server:
    def __init__(
        self,
        server_address: tuple[str, int],
        memory_range: tuple[int, int],
        server_addresses: list[tuple[str, int]],
        memory_ranges: list[tuple[int, int]],
    ):
        self.server_address = server_address
        self.memory_range = memory_range
        self.server_addresses = server_addresses
        self.memory_ranges = memory_ranges

        self.memory_manager = mm.MemoryManager(memory_range=self.memory_range)
        self.shared_memory = cache.Cache(cache_size=CACHE_SIZE)

    def start(self):
        """
        Description:
        - Start the server and listen for incoming connections from clients

        Return:
        - None
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(self.server_address)
            server_socket.listen()

            log_msg(f"[LISTENING] Server is listening on {self.server_address}")

            while True:
                # accept new connection
                # and create a new thread to handle the client
                # this allows for multiple clients to connect to the server
                # at the same time
                client_socket, client_address = server_socket.accept()
                thread = th.Thread(
                    target=self.handle_client, args=(client_socket, client_address)
                )
                thread.start()
                # th.active_count() - 1 because the main thread is also counted
                # as an active thread. Sometimes, this result might still not be
                # accurate because we might have lock-leasing threads that are still active
                # but of course do not count as active connections.
                log_msg(
                    f"[ACTIVE CONNECTIONS] Active connections: {th.active_count() - 1}"
                )

    def handle_client(
        self, client_socket: socket.socket, client_address: tuple[str, int]
    ):
        """
        Description:
        - Handle a client connection by receiving messages from the client
        and sending back the appropriate responses
        """
        log_msg(f"[NEW CONNECTION] {client_address} connected.")
        connected = True

        # keep the connection open until the client sends a disconnect message
        # or communication errors occur
        while connected:
            return_data = None
            message = None
            try:
                message = cu.rec_msg(client_socket)
            except Exception as e:
                log_msg(
                    f"[ERROR RECEIVING] server {self.server_address}, client {client_address}: {e}"
                )
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
            elif message["type"] == "serve_dump_cache":
                return_data = self.serve_dump_cache(client_address)
            else:
                return_data = {
                    "status": gv.INVALID_OPERATION,
                    "message": "invalid message type",
                }

            try:
                cu.send_msg(client_socket, return_data)
            except Exception as e:
                log_msg(
                    f"[ERROR SENDING] server {self.server_address}, client {client_address}: {e}"
                )
                break

        log_msg(
            f"[DISCONNECTED] server {self.server_address}, client {client_address}."
        )

        try:
            # client_socket.shutdown(socket.SHUT_RDWR)
            client_socket.close()
        except Exception as e:
            log_msg(
                f"[ERROR CLOSING] server {self.server_address}, client {client_address}: {e}"
            )

    def serve_read(
        self,
        client_address: tuple[str, int],
        copy_holder_ip: str,
        copy_holder_port: int,
        memory_address: int,
        cascade: bool,
        lease_timeout=LEASE_TIMEOUT,
    ):
        """
        Description:
        - Handle a read request from a client
        - If the memory address is in the server's memory range, the server
        reads the data from its memory and sends it back to the client
        - If the memory address is not in the server's memory range, the server
        forwards the request to the appropriate server

        We should explain the cascade parameter: if cascade is True, the server
        will forward the request if it doesn't find it locally. If cascade is False,
        the server will return an error if it doesn't find the memory address locally.

        Clients outside the system are setup to make requests with cascade=True.

        Thus, we have the following behaviour:
        cascade=True, address is local: outside client made a request to the server that owns the memory address
        cascade=True, address is not local: outside client made a request to a server that doesn't own the memory address
        cascade=False, address is local: inside client (another server) made a request to the server that owns the memory address
        cascade=False, address is not local: this is the most interesting one and it should never happen. It occurs when a server
        wants to find a memory address that is not local to it. This server requests the address from the server that it thinks owns
        the address, but that server doesn't have the memory address either. Our system is setup such that all servers should know
        which server has what memory addresses, thus this should never happen.
        """
        # potentially new holder of the memory address
        copy_holder = (copy_holder_ip, copy_holder_port)
        log_msg(
            f"[READ REQUEST] server {self.server_address}, client {client_address}, address {memory_address}"
        )
        host_server = self._get_server_address(memory_address)
        if host_server is None:
            return {
                "status": gv.INVALID_ADDRESS,
                "message": "Memory address out of range",
            }

        if host_server == self.server_address:
            # if the memory address is in the server's memory range
            # read the data from the server's memory and send it back to the client
            # we use locks to ensure atomicity
            data = None
            ltag = -1
            try:
                ret_val, ltag, wtag = self.memory_manager.acquire_lock(memory_address)
                if not ret_val:
                    return {"status": gv.ERROR, "message": "Failed to acquire lock"}
                # cascade=False means this should be the server that owns the memory address
                # and the copyholder address should be from another server and not an outside client
                # thus, we add the copy holder to the memory address
                if not cascade and copy_holder != self.server_address:
                    self.memory_manager.add_copy_holder(memory_address, copy_holder)
                data = self.memory_manager.read_memory(memory_address)
            finally:
                self.memory_manager.release_lock(memory_address, ltag)
            data = data.json()
            response = {
                "status": gv.SUCCESS,
                "message": "read successful",
                **data,
                "ltag": ltag,
            }
            log_msg(
                f"[READ RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}"
            )
            return response

        # if the memory address is in the server's shared cache
        # read the data from the shared cache and send it back to the client
        # we request a lock from the server that owns the memory address
        # we compare the wtags (last write tags) to make sure that the cached data is up-to-date
        mem_item = self.shared_memory.read(memory_address)
        
        if mem_item is not None:
            ac_lock_val = self.serve_acquire_lock(
                self.server_address, memory_address, lease_timeout, True
            )
            if ac_lock_val["status"] != gv.SUCCESS:
                self.shared_memory.remove(memory_address)
                return ac_lock_val
            
            if ac_lock_val["wtag"] == mem_item.wtag:
                return_value = mem_item.json()
                rel_lock_val = self.serve_release_lock(
                    self.server_address,
                    memory_address,
                    ac_lock_val["ltag"],
                    True,
                )

                if rel_lock_val["status"] != gv.SUCCESS:
                    self.shared_memory.remove(memory_address)
                    return rel_lock_val

                if rel_lock_val["wtag"] != mem_item.wtag:
                    # stale data in cache, fetch from server
                    self.shared_memory.remove(memory_address)
                    return self.serve_read(
                        client_address,
                        copy_holder_ip,
                        copy_holder_port,
                        memory_address,
                        cascade,
                    )

                log_msg(
                    f"[READ RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}"
                )
                return {
                    "status": gv.SUCCESS,
                    "message": "read successful",
                    **return_value,
                    "ltag": ac_lock_val["ltag"],
                }
            else:  # give up and then just communicate with the server
                # stale data in cache, fetch from server
                self.shared_memory.remove(memory_address)

                rel_lock_val = self.serve_release_lock(
                    self.server_address,
                    memory_address,
                    ac_lock_val["ltag"],
                    True,
                )

                if rel_lock_val["status"] != gv.SUCCESS:
                    return rel_lock_val

                return self.serve_read(
                    client_address,
                    copy_holder_ip,
                    copy_holder_port,
                    memory_address,
                    cascade,
                )

        if not cascade:  # this should never happen (see explanation above)
            return {
                "status": gv.ERROR,
                "message": f"Read host address {host_server} is not the server address {self.server_address}",
            }

        ip, port = self.server_address
        remote_return = self._get_from_remote(
            client_address,
            memory_address,
            host_server,
            "serve_read",
            [ip, port, memory_address, False],
            "READ",
        )

        # if requested from remote server, update shared cache
        if remote_return["status"] == gv.SUCCESS:
            self.shared_memory.write(
                memory_address,
                remote_return["data"],
                remote_return["istatus"],
                remote_return["wtag"],
            )
        return remote_return

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
        Description:
        - Handle a write request from a client
        - If the memory address is in the server's memory range, the server
        writes the data to its memory and sends back a success message to the client.
        The server also sends updates to all copyholders of the memory address.
        This is the main implementation of the write-update protocol.

        - If the memory address is not in the server's memory range, the server
        forwards the request to the appropriate server
        """
        copy_holder = (copy_holder_ip, copy_holder_port)
        log_msg(
            f"[WRITE REQUEST] server {self.server_address}, client {client_address}, address {memory_address}"
        )
        host_server = self._get_server_address(memory_address)
        if host_server is None:
            return {
                "status": gv.INVALID_ADDRESS,
                "message": "Memory address out of range",
            }

        if host_server == self.server_address:
            ltag = -1
            try:
                ret_val, ltag, wtag = self.memory_manager.acquire_lock(memory_address)
                if not ret_val:
                    return {"status": gv.ERROR, "message": "Failed to acquire lock"}
                # cascade=False means this should be the server that owns the memory address
                # and the copyholder address should be from another server and not an outside client
                # thus, we add the copy holder to the memory address
                if not cascade and copy_holder != self.server_address:
                    self.memory_manager.add_copy_holder(memory_address, copy_holder)
                self.memory_manager.write_memory(memory_address, data)
                # update shared copies in the system, if they exist!
                if self.memory_manager.read_memory(memory_address).status == "S":
                    self._update_shared_copies(client_address, memory_address)
            finally:
                self.memory_manager.release_lock(memory_address, ltag)
            response = {
                "status": gv.SUCCESS,
                "message": "write successful",
            }
            log_msg(
                f"[WRITE RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}"
            )
            return response

        if not cascade:  # this should never happen (see explanation above)
            return {
                "status": gv.ERROR,
                "message": f"Write host address {host_server} is not the server address {self.server_address}",
            }

        # if the memory address is not in the server's memory range
        # forward the request to the appropriate server
        ip, port = self.server_address
        return self._get_from_remote(
            client_address,
            memory_address,
            host_server,
            "serve_write",
            [ip, port, memory_address, data, False],
            "WRITE",
        )

    # serve_acquire_lock and serve_release_lock are used to acquire and release locks
    # they have very similar build to serve_read and serve_write

    def serve_acquire_lock(
        self,
        client_address: tuple[str, int],
        memory_address: int,
        lease_timeout: float,
        cascade: bool,
    ):
        log_msg(
            f"[ACQUIRE LOCK REQUEST] server {self.server_address}, client {client_address}, memory address {memory_address}"
        )
        host_server = self._get_server_address(memory_address)
        if host_server is None:
            return {
                "status": gv.INVALID_ADDRESS,
                "message": "Memory address out of range",
            }

        if host_server == self.server_address:
            try:
                ret_val, ltag, wtag = self.memory_manager.acquire_lock(
                    memory_address, lease_timeout
                )

                response = None
                if ret_val:
                    response = {
                        "status": gv.SUCCESS,
                        "message": "lock acquired",
                        "ret_val": ret_val,
                        "ltag": ltag,
                        "wtag": wtag,
                    }
                else:
                    response = {"status": gv.ERROR, "message": "lock not acquired"}
                log_msg(
                    f"[ACQUIRE LOCK RESPONSE] server {self.server_address}, client {client_address}, memory address {memory_address}"
                )
            except Exception as e:
                response = {
                    "status": gv.ERROR,
                    "message": f"Failed to acquire lock with error: {e}",
                }
            finally:
                return response

        if not cascade:
            return {
                "status": gv.ERROR,
                "message": f"Lock host address {host_server} is not the server address {self.server_address}",
            }

        return self._get_from_remote(
            client_address,
            memory_address,
            host_server,
            "serve_acquire_lock",
            [memory_address, lease_timeout, False],
            "ACQUIRE LOCK",
        )

    def serve_release_lock(
        self,
        client_address: tuple[str, int],
        memory_address: int,
        ltag: int,
        cascade: bool,
    ):
        log_msg(
            f"[RELEASE LOCK REQUEST] server {self.server_address}, client {client_address}, address {memory_address}"
        )
        host_server = self._get_server_address(memory_address)
        if host_server is None:
            return {
                "status": gv.INVALID_ADDRESS,
                "message": "Memory address out of range",
            }

        if host_server == self.server_address:
            ret_val, ltag, wtag = self.memory_manager.release_lock(memory_address, ltag)
            response = None
            if ret_val:
                response = {
                    "status": gv.SUCCESS,
                    "message": "lock released",
                    "ret_val": ret_val,
                    "ltag": ltag,
                    "wtag": wtag,
                }
            else:
                response = {
                    "status": gv.SUCCESS,
                    "message": "lock was already released",
                    "ret_val": ret_val,
                    "ltag": ltag,
                    "wtag": wtag,
                }
            log_msg(
                f"[RELEASE LOCK RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}"
            )
            return response

        if not cascade:
            return {
                "status": gv.ERROR,
                "message": f"Lock host address {host_server} is not the server address {self.server_address}",
            }

        return self._get_from_remote(
            client_address,
            memory_address,
            host_server,
            "serve_release_lock",
            [memory_address, ltag, False],
            "RELEASE LOCK",
        )

    def serve_update_cache(
        self,
        client_address: tuple[str, int],
        address_chain: list[tuple[str, int]],
        memory_address: int,
        data,
        status: str,
        wtag: int,
    ):
        """
        Description:
        - Update the local cache copy of a memory address and notify the next server in the address chain
        """
        aux_address_chain = []
        for address in address_chain:
            aux_address_chain.append((address[0], address[1]))
        address_chain = aux_address_chain  # turn them back into tuples (from lists)

        print(
            f"[UPDATE CACHE REQUEST] server {self.server_address}, client {client_address}, address {memory_address}"
        )
        host_server = self._get_server_address(memory_address)
        if host_server is None:
            return {
                "status": gv.INVALID_ADDRESS,
                "message": "Memory address out of range",
            }

        if (
            host_server != self.server_address
        ):  # a host server doesn't need to update its cache
            self._update_local_copy(memory_address, data, status, wtag)

        if len(address_chain) > 0:
            next_address = address_chain.pop(0)
            response = self._update_next_copy(
                address_chain, next_address, memory_address, data, status, wtag
            )
            print(
                f"[UPDATE CACHE RESPONSE] server {self.server_address}, client {client_address}, address {memory_address}, response {response}"
            )
            return response

        return {
            "status": gv.SUCCESS,
            "message": "cache updated",
        }

    def _update_shared_copies(
        self,
        client_address: tuple[str, int],
        memory_address: int,
    ):
        """
        Description: a server starts updating shared copies of a memory address.
        The server keeps track of a copyholder address chain and instead of sending
        requests to all copyholders at once, it sends a request to the first copyholder
        in the chain and then each copyholder sends a request to the next copyholder in the chain.

        The server keeps track of the copyholder address chain and if a copyholder fails to update
        the shared copy, the server removes all copyholders after the failed copyholder in the chain (
        including the failed copyholder itself). This is done to ensure that the shared copies are
        consistent across all servers.
        """
        address_chain = self.memory_manager.get_copy_holders(memory_address)

        update_value = self.serve_update_cache(
            client_address,
            address_chain,
            memory_address,
            self.memory_manager.read_memory(memory_address).data,
            self.memory_manager.read_memory(memory_address).status,
            self.memory_manager.read_memory(memory_address).wtag,
        )

        print("-" * 50)
        log_msg(f"[UPDATE SHARED COPIES] {update_value}")

        if update_value["status"] != gv.SUCCESS:
            failed_address = update_value.get("server_address", None)
            if failed_address is None:
                failed_address = address_chain[
                    0
                ]  # the address chain has at least one item if this function is called
            failed_address = (
                failed_address[0],
                failed_address[1],
            )  # turn it into a tuple again

            for i, address in enumerate(address_chain):
                if i >= address_chain.index(failed_address):
                    self.memory_manager.remove_copy_holder(memory_address, address)

        log_msg(
            f"[UPDATE SHARED COPIES] COPY HOLDERS: {self.memory_manager.get_copy_holders(memory_address)}"
        )
        print("-" * 50)

    def serve_dump_cache(
        self,
        client_address: tuple[str, int],
    ):
        """
        Description:
        - Dump the server's cache, used for debugging purposes
        """
        log_msg(
            f"[DUMP CACHE REQUEST] server {self.server_address}, client {client_address}"
        )
        cache_items = [
            {
                "address": self.shared_memory.key_map[i],
                **self.shared_memory.read_no_sync(self.shared_memory.key_map[i]).json(),
            }
            for i in range(self.shared_memory.cache_size)
            if self.shared_memory.key_map[i] is not None
        ]

        return {
            "status": gv.SUCCESS,
            "message": "cache dumped",
            "cache": cache_items,
        }

    def _update_local_copy(
        self,
        memory_address: int,
        data,
        status: str,
        wtag: int,
    ):
        self.shared_memory.write(memory_address, data, status, wtag)
        return True

    def _update_next_copy(
        self,
        address_chain: list[tuple[str, int]],
        next_address: tuple[str, int],
        memory_address: int,
        data,
        status: str,
        wtag: int,
    ):
        ret_val = self._get_from_remote(
            self.server_address,
            memory_address,
            next_address,
            "serve_update_cache",
            [address_chain, memory_address, data, status, wtag],
            "UPDATE CACHE",
        )

        # if the next server in the chain fails to update the shared copy
        # then this server is the first to fail and we need to update the copyholder list
        # to remove all servers after the failed server in the chain (including the failed server)
        if ret_val["status"] != gv.SUCCESS and "server_address" not in ret_val:
            ret_val["server_address"] = next_address

        return ret_val

    def _get_from_remote(
        self,
        client_address: tuple[str, int],
        memory_address: int,
        host_server: tuple[str, int],
        type: str,
        args: list[any],
        log_type: str,
    ):
        """
        Description:
        Wrapper function to connect to a remote server and send a message.
        It is used when our requests want to retrieve something from another server.
        """
        host_server_socket = None
        response = None
        try:
            host_server_socket = self._connect_to_server(
                host_server, CONNECTION_TIMEOUT
            )
            cu.send_msg(host_server_socket, {"type": type, "args": args})
            response = cu.rec_msg(host_server_socket)
            log_msg(
                f"[{log_type} RESPONSE] server {self.server_address}, client {client_address}, memory address {memory_address}"
            )
        except Exception as e:
            log_msg(
                f"[{log_type} ERROR] server {self.server_address}, client {client_address}, memory address {memory_address}: {e}"
            )
            response = {
                "status": gv.ERROR,
                "message": f"Failed to connect to the host with error: {e}",
            }
        finally:
            try:
                if host_server_socket is not None:
                    self._disconnect_from_server(host_server_socket)
            except Exception as e:
                log_msg(
                    f"[{log_type} ERROR DISCONNECTING INTERNAL] server {self.server_address}, client {client_address}, memory address {memory_address}: {e}"
                )
        return response

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

    def _get_server_address(self, memory_address: int) -> None | tuple[str, int]:
        """
        Input:
        - memory_address: the memory address to get the server address for

        Return:
        - server_address: the address of the server that contains the memory address
        """
        server_index = self._get_server_index(memory_address)
        if server_index == -1:
            return None
        return self.server_addresses[server_index]

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
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
            cu.send_msg(server_socket, {"type": "disconnect"})
            cu.rec_msg(server_socket)
        finally:
            # server_socket.shutdown(socket.SHUT_RDWR)
            server_socket.close()


def start_server_process(server_index: int):
    """
    Description: given a server index, start the server process
    This function finds the memory range and network address that this server
    should use and starts the server process with these parameters
    """
    memory_size = gv.MEMORY_SIZE
    server_count = len(gv.SERVERS)
    server_memory_size = memory_size // server_count
    memory_ranges = []
    for i in range(server_count):
        memory_ranges.append((i * server_memory_size, (i + 1) * server_memory_size))
    net_addresses = gv.SERVERS
    net_address = net_addresses[server_index]
    memory_range = memory_ranges[server_index]
    server = Server(net_address, memory_range, net_addresses, memory_ranges)
    server.start()


import argparse


def main():
    parser = argparse.ArgumentParser(description="Start a server process")
    parser.add_argument(
        "-server",
        type=int,
        help="The index of the server in the list of servers",
        required=True,
    )
    args = parser.parse_args()
    start_server_process(int(args.server))


if __name__ == "__main__":
    main()
