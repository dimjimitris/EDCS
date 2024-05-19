import threading as th

import utils


class MemoryItem:
    def __init__(
        self,
        data,
        status,
        tag=utils.get_time(),
    ):
        self.data = data
        self.status = status
        self.tag = tag

    def __str__(self) -> str:
        return f"{self.data}, {self.status}"
    
    def json(self):
        return {
            "data": self.data,
            "istatus": self.status, # item status
            "tag": self.tag,
        }
            
# let's do this without deadlocks
class LockItem:
    def __init__(self):
        self.lock = th.Lock()
        self.condition = th.Condition()
        self.counter = utils.get_time()

    def acquire_lock(self, lease_time=0):
        """
        Input:
        - lease: if 0, lock is acquired indefinitely, otherwise, lock is acquired for lease_time seconds

        Return:
        - ret_val: True if lock is acquired, False otherwise
        - counter: counter of the lock
        - time: time when the lock was acquired
        """
        ret_val, counter = None, -1
        with self.condition:
            while self.lock.locked():
                self.condition.wait()
            ret_val = self.lock.acquire()
            if ret_val:
                self.counter += 1
            counter = self.counter

        if ret_val and lease_time > 0:
            th.Timer(lease_time, self.release_lock, args=(self.counter, True)).start()

        return ret_val, counter, utils.get_time()
    
    def release_lock(self, lease_counter, increment_counter=False):
        """
        Input:
        - lease_counter: the counter of the lock when it was acquired
        - increment_counter: if True, increment the counter by 1

        Return:
        - ret_val: True if lock is released, False if it was already released
        - counter: counter of the lock
        - time: time when the lock was released
        """
        ret_val, counter = None, -1
        with self.condition:
            counter = self.counter
            if self.counter == lease_counter:
                self.counter = self.counter + 1 if increment_counter else self.counter
                counter = self.counter
                self.lock.release()
                self.condition.notify_all()
                ret_val = True
            else:
                ret_val = False

        return ret_val, counter, utils.get_time()