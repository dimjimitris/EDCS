import threading as th

import time_utils


class MemoryItem:
    def __init__(
        self,
        data,
        status,  # 'E': exclusive, 'S': shared
        wtag=time_utils.get_time(),  # last write tag
    ):
        self.data = data
        self.status = status
        self.wtag = wtag

    def __str__(self) -> str:
        return f"{self.data}, {self.status}"

    def json(self) -> dict:
        """
        Description: This function returns the MemoryItem object as a dictionary.
        To be used when sending the object over the network.
        """
        return {
            "data": self.data,
            "istatus": self.status,  # item status
            "wt": self.wtag,
        }


class LockItem:
    def __init__(self):
        self.lock = th.Lock()
        self.condition = th.Condition()
        self.ltag = time_utils.get_time()  # last lock tag

    def acquire_lock(self, lease_seconds=None) -> tuple[bool, int]:
        ret_val, ltag = None, -1
        with self.condition:
            while self.lock.locked():
                self.condition.wait()
            ret_val = self.lock.acquire()
            if ret_val:
                self.ltag += 1
            ltag = self.ltag

        if ret_val and lease_seconds is not None:
            th.Timer(lease_seconds, self.release_lock, args=(self.ltag, True)).start()

        return ret_val, ltag

    def release_lock(self, lease_ltag) -> tuple[bool, int]:
        ret_val, ltag = False, -1
        with self.condition:
            ltag = self.ltag
            if self.ltag == lease_ltag:
                self.ltag += 1

                ret_val = True
                ltag = self.ltag
                self.lock.release()
                self.condition.notify_all()

        return ret_val, ltag
