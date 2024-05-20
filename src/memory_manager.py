import memory_primitives as mp

class MemoryManager:
    def __init__(
        self,
        memory_range,
    ):
        self.memory_range = memory_range

        self.memory = {
            i: mp.MemoryItem(
                data=None,
                status="E",
            )
            for i in range(self.memory_range[0], self.memory_range[1])
        }

        self.locks = {
            i: mp.LockItem() for i in range(self.memory_range[0], self.memory_range[1])
        }

        self.copy_holders : dict[int, set[tuple[str, int]]] = {
            i: set() for i in range(self.memory_range[0], self.memory_range[1])
        }

    def read_memory(self, address):
        """
        Input:
        - address: the address to read from

        Return:
        - memory_item: the memory item at the address or None if the address is out of range
        """
        if address not in self.memory:
            return None
        return self.memory[address]

    def write_memory(self, address, data):
        """
        Input:
        - address: the address to write to
        - data: the data to write

        Return:
        - ret_val: True if write is successful, False otherwise
        """
        if address not in self.memory:
            return False
        self.memory[address].data = data
        self.memory[address].tag += 1
        return True

    def acquire_lock(self, address, lease_time=0):
        """
        Input:
        - address: the address to acquire lock for
        - lease_time: if 0, lock is acquired indefinitely, otherwise, lock is acquired for lease_time seconds

        Return:
        - ret_val: True if lock is acquired, False otherwise
        - counter: counter of the lock
        - tag: tag of the memory item
        """
        if address not in self.locks:
            return False, -1, -1
        ret_val, counter = self.locks[address].acquire_lock(lease_time)
        return (
            ret_val,
            counter,
            self.memory[address].tag,
        )

    def release_lock(self, address, lease_counter, increment_counter=False):
        """
        Input:
        - address: the address to release lock for
        - lease_counter: the counter of the lock when it was acquired
        - increment_counter: if True, increment the counter by 1

        Return:
        - ret_val: True if lock is released, False if it was already released
        - counter: counter of the lock
        - tag: tag of the memory item
        """
        if address not in self.locks:
            return False, -1, -1

        tag = self.memory[address].tag
        ret_val, counter = self.locks[address].release_lock(
            lease_counter, increment_counter
        )
        return (
            ret_val,
            counter,
            tag,
        )
    
    def set_status(self, address, status):
        """
        Input:
        - address: the address to set status for
        - status: the status to set

        Return:
        - True if status is set, False otherwise
        """
        if address not in self.memory:
            return False
        self.memory[address].status = status
        return True

    def get_copy_holders(self, address):
        """
        Input:
        - address: the address to get copy holders for

        Return:
        - the set of copy holders for the address
        """
        if address not in self.memory:
            return set()
        return self.copy_holders[address]

    def add_copy_holder(self, address, holder):
        """
        Input:
        - address: the address to add holder for
        - holder: the holder to add

        Return:
        - True if holder is added, False otherwise
        """
        if address not in self.memory:
            return False
        self.copy_holders[address].add(holder)
        self.memory[address].status = "S"
        return True
    
    def remove_copy_holder(self, address, holder):
        """
        Input:
        - address: the address to remove holder for
        - holder: the holder to remove

        Return:
        - True if holder is removed, False otherwise
        """
        if address not in self.memory:
            return False
        
        if holder in self.copy_holders[address]:
            self.copy_holders[address].remove(holder)
            if len(self.copy_holders[address]) == 0:
                self.memory[address].status = "E"
            return True
        else:
            return False