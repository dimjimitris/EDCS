import random
import socket

import comm_utils as cu
import global_variables as gv


class Client:
    """
    Description: software that runs on a client machine and provides
    an interface to interact with the server.
    """
    def __init__(
        self,
        server_address=random.choice(gv.SERVERS),
    ):
        self.server_address = server_address
        # self.s.settimeout(3 * gv.CONNECTION_TIMEOUT)

    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.settimeout(3 * gv.CONNECTION_TIMEOUT)
        self.s.connect(self.server_address)

    def disconnect(self):
        data = None
        try:
            cu.send_msg(self.s, {"type": "disconnect"})
            data = cu.rec_msg(self.s)
        finally:
            self.s.close()
            return data

    def write(self, mem_address, data):
        """
        Write data to memory address
        """
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

    def read(self, mem_address):
        """
        read data from memory address
        """
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

    def acquire_lock(self, mem_address):
        """
        Acquire lock for item at memory address
        """
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
    
    def release_lock(self, mem_address, ltag):
        """
        Release lock for item at memory address

        ltag: lease tag when the lock was acquired
        """
        cu.send_msg(
            self.s,
            {
                "type": "serve_release_lock",
                "args": [
                    mem_address,
                    ltag,
                    True,
                ],
            }
        )
        data = cu.rec_msg(self.s)
        return data

    def dump_cache(self):
        """
        Dump the cache of the server
        """
        cu.send_msg(self.s, {"type": "serve_dump_cache"})
        data = cu.rec_msg(self.s)
        return data