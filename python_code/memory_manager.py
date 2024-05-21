import memory_primitives as mp

class MemoryManager:
    def __init__(
        self,
        memory_range : tuple[int, int],
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

        self.copy_holders : dict[int, list[tuple[str, int]]] = {
            i: [] for i in range(self.memory_range[0], self.memory_range[1])
        }

    def read_memory(self, address: int) -> None | mp.MemoryItem:
        if address not in self.memory:
            return None
        return self.memory[address]
    
    def write_memory(self, address: int, data) -> None | mp.MemoryItem:
        if address not in self.memory:
            return None
        self.memory[address].data = data
        self.memory[address].wtag += 1
        return self.memory[address]
    
    def acquire_lock(self, address: int, lease_seconds=None) -> tuple[bool, int, int]:
        """
        Return:
        - ret_val: True if the lock is acquired, False otherwise
        - ltag: the lock tag
        - wtag: the write tag
        """
        if address not in self.locks:
            return False, -1, -1
        ret_val, ltag = self.locks[address].acquire_lock(lease_seconds)
        return ret_val, ltag, self.memory[address].wtag
    
    def release_lock(self, address: int, lease_ltag) -> tuple[bool, int, int]:
        """
        Return:
        - ret_val: True if the lock is released, False otherwise
        - ltag: the lock tag
        - wtag: the write tag
        """
        if address not in self.locks:
            return False, -1, -1
        wtag = self.memory[address].wtag
        ret_val, ltag = self.locks[address].release_lock(lease_ltag)
        return ret_val, ltag, wtag
    
    def set_status(self, address: int, status: str) -> bool:
        if address not in self.memory:
            return False
        self.memory[address].status = status
        return True

    def get_copy_holders(self, address: int) -> list[tuple[str, int]]:
        if address not in self.copy_holders:
            return []
        return self.copy_holders[address].copy()
    
    def add_copy_holder(self, address: int, holder: tuple[str, int]) -> bool:
        """
        Return:
        - True: if the holder is in the copy_holders list
        """
        if address not in self.copy_holders:
            return False
        if holder in self.copy_holders[address]:
            return True
        self.copy_holders[address].append(holder)
        self.memory[address].status = "S"
        return True
    
    def remove_copy_holder(self, address: int, holder: tuple[str, int]) -> bool:
        """
        Return:
        - True: if the holder is not in the copy_holders list
        """
        if address not in self.copy_holders:
            return False
        if holder not in self.copy_holders[address]:
            return True
        self.copy_holders[address].remove(holder)
        if len(self.copy_holders[address]) == 0:
            self.memory[address].status = "E"
        return True
    