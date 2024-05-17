import memory_item as mi
import threading

class MemoryManager:
    def __init__(
        self,
        memory_range,
    ):
        
        self.memory = {
            i: mi.MemoryItem(None, "E")
            for i in range(memory_range[0], memory_range[1])
        }

        self.locks = {
            i: threading.Lock()
            for i in range(memory_range[0], memory_range[1])
        }

    def acquire_lock(self, address):
        self.locks[address].acquire()

    def release_lock(self, address):
        self.locks[address].release()

    def read(self, address):
        return self.memory[address]
    
    def write(self, address, data):
        self.memory[address].data = data

    def set_status(self, address, status):
        self.memory[address].status = status

    def get_range(self):
        return list(self.memory.keys())