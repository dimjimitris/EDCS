import random
import socket

import comm_utils as cu
import global_variables as gv


class Client:
    def __init__(
        self,
        server_address=random.choice(gv.SERVERS),
    ):
        self.server_address = server_address
        # self.s.settimeout(3 * gv.CONNECTION_TIMEOUT)

    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(3 * gv.CONNECTION_TIMEOUT)
        self.s.connect(self.server_address)

    def disconnect(self):
        cu.send_msg(self.s, {"type": "disconnect"})
        data = cu.rec_msg(self.s)
        self.s.close()
        return data

    def write(self, mem_address, data):
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
