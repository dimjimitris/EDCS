import threading as th

import memory_primitives as mp


class Cache:
    def __init__(
        self,
        cache_size: int,
    ):
        self.cache_size = cache_size
        self.key_map = {i: None for i in range(cache_size)}
        self.cache = {i: None for i in range(cache_size)}
        self.locks = {i: th.Lock() for i in range(cache_size)}

    def check_key(self, memory_address: int) -> bool:
        key = memory_address % self.cache_size
        return self.key_map[key] == memory_address

    def read(self, memory_address: int) -> None | mp.MemoryItem:
        key = memory_address % self.cache_size
        if self.key_map[key] != memory_address:
            return None
        return self.cache[key]
    
    def write(
            self,
            memory_address: int,
            data,
            status: str,
            wtag: int,
        ) -> None | mp.MemoryItem:
        key = memory_address % self.cache_size
        if self.key_map[key] == memory_address:
            self.cache[key].data = data
            self.cache[key].status = status
            self.cache[key].wtag = wtag
            return self.cache[key]
        else:
            self.key_map[key] = memory_address
            self.cache[key] = mp.MemoryItem(
                data=data,
                status=status,
                wtag=wtag,
            )
            return self.cache[key]
        
    def remove(self, memory_address: int) -> None:
        key = memory_address % self.cache_size
        if self.key_map[key] == memory_address:
            self.key_map[key] = None
            self.cache[key] = None
        
    def get_lock(self, memory_address: int) -> th.Lock:
        key = memory_address % self.cache_size
        return self.locks[key]