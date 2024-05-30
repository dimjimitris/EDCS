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
            "wtag": self.wtag,
        }


class LockItem:
    def __init__(self):
        self.lock = th.Lock() # lock for the item
        self.condition = th.Condition() # condition + lock that protect the (item) lock
        self.ltag = time_utils.get_time()  # last lock tag

    def acquire_lock(self, lease_seconds=None) -> tuple[bool, int]:
        """
        Description: This function acquires the lock for the item.

        return: (bool, int) -> (success, ltag)
        """
        ret_val, ltag = False, -1
        # we want to acquire the lock and increment the ltag atomically
        # thus we use a condition variable to wait until the lock is acquired
        # and then increment the ltag
        with self.condition:
            while self.lock.acquire(blocking=False) is False:
                self.condition.wait()
            ret_val = True
            self.ltag += 1
            ltag = self.ltag

        # the lease seconds applies if the lock is acquired by a remote client
        # this client could potentially fail and keep the lock forever, thus
        # we release the lock after the lease_seconds
        if ret_val and lease_seconds is not None:
            def timer_callback():
                if self.release_lock(ltag):
                    print("[LOCK TIMER] lock released")
            th.Timer(lease_seconds, timer_callback).start()

        return ret_val, ltag

    def release_lock(self, lease_ltag) -> tuple[bool, int]:
        """
        Description: This function releases the lock for the item.

        return: (bool, int) -> (success, ltag)
        """
        ret_val, ltag = False, -1
        # again we want to release the lock and update the ltag atomically
        # thus we use acquire the condition variable's lock before releasing the item's lock
        with self.condition:
            ltag = self.ltag
            # we only release the lock if the lease_ltag is the same as the current ltag
            # this is to prevent a client from releasing the lock if it has been acquired by another client
            # senario where this happens is: client1 acquires the lock, client1 loses connection, the timer
            # expires and releases the lock, client2 acquires the lock, client1 reconnects and releases the lock

            # This senario cannot happen because the new ltag will be different than the one client1 has.
            if self.ltag == lease_ltag:
                self.ltag += 1

                ret_val = True
                ltag = self.ltag
                self.lock.release()
                self.condition.notify_all()

        return ret_val, ltag
