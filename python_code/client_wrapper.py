import jpype
from jpype import imports
from jpype.types import *
import json

import client_logic as cl
import global_variables as gv


class ClientWrapper:
    def __init__(
        self,
        type: str,
        server_address: tuple[str, int],
    ):
        self.type = type
        self.client = None
        self.server_address = server_address
        if type == "java":
            # Load the Java ClientLogic class
            self.ClientLogic = jpype.JClass("main.edcs.project.ClientLogic")
        elif type == "python":
            self.ClientLogic = cl.Client

    def connect(self):
        if self.type == "java":
            self.client = self.ClientLogic(
                self.server_address[0], self.server_address[1]
            )
            self.client.connect()
        elif self.type == "python":
            self.client = self.ClientLogic(self.server_address)
            self.client.connect()

    def disconnect(self):
        resp = self.client.disconnect()
        return self._treat_java_response(resp)

    def read(self, address: int):
        resp = self.client.read(address)
        return self._treat_java_response(resp)

    def write(self, address: int, data):
        try:
            data = int(data)
        except:
            pass
        resp = self.client.write(address, data)
        return self._treat_java_response(resp)

    def acquire_lock(self, address: int):
        if self.type == "python":
            resp = self.client.acquire_lock(address)
        elif self.type == "java":
            resp = self.client.acquireLock(address)
        return self._treat_java_response(resp)

    def release_lock(self, address: int, lease_tag: int):
        if self.type == "python":
            resp = self.client.release_lock(address, lease_tag)
        elif self.type == "java":
            resp = self.client.releaseLock(address, lease_tag)
        return self._treat_java_response(resp)

    def dump_cache(self):
        if self.type == "python":
            resp = self.client.dump_cache()
        elif self.type == "java":
            resp = self.client.dumpCache()
        return self._treat_java_response(resp)

    def _treat_java_response(self, response):
        if self.type == "java":
            response = response.toString()
            response = str(response)
            return json.loads(response)
        return response
