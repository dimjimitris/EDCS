package main.java.project;

import java.util.Timer;
import java.util.TimerTask;
import java.util.concurrent.Semaphore;

public class LockItem {
    // as opposed to the python version, we do not have an explicit condition
    // we use the condition variable and the lock provided by java with the
    // synchronized keyword
    private Semaphore lock; // lock for the item
    private long ltag; // last lock tag

    public LockItem() {
        this.lock = new Semaphore(1);
        this.ltag = TimeUtils.getTime();
    }

    // this function acquires the lock for the item.
    // returns a Tuple which indicates if acquiring the lock was successful
    // and what the last lock tag is.
    public Tuple<Boolean, Long> acquireLock(Long leaseSeconds) throws InterruptedException {
        boolean retVal = false;
        long ltag = -1;
        // we want to acquire the lock and increment the ltag atomically
        // thus we use a condition variable to wait until the lock is acquired
        // and then increment the ltag
        synchronized (this) {
            while (!this.lock.tryAcquire()) {
                this.wait();
            }
            retVal = true;
            this.ltag += 1;
            ltag = this.ltag;
        }

        // the lease seconds applies if the lock is acquired by a remote client
        // this client could potentially fail and keep the lock forever, thus
        // we release the lock after the lease_seconds
        if (retVal && leaseSeconds != null) {
            long finalLtag = ltag;
            new Timer().schedule(new TimerTask() {
                @Override
                public void run() {
                    releaseLock(finalLtag);
                    System.out.println("[LOCK TIMER] lock released");
                }
            }, leaseSeconds * 1000L);
        }
        return new Tuple<>(retVal, ltag);
    }

    // this function releases the lock for an item.
    // returns Tuple of (boolean, long) -> (success, ltag)
    public Tuple<Boolean, Long> releaseLock(long leaseLtag) {
        boolean retVal = false;
        long ltag = -1;

        // again we want to release the lock and update the ltag atomically
        // thus we use acquire the condition variable's lock before releasing the item's lock
        synchronized (this) {
            ltag = this.ltag;
            // we only release the lock if the lease_ltag is the same as the current ltag
            // this is to prevent a client from releasing the lock if it has been acquired by another client
            // senario where this happens is: client1 acquires the lock, client1 loses connection, the timer
            // expires and releases the lock, client2 acquires the lock, client1 reconnects and releases the lock

            // This senario cannot happen because the new ltag will be different than the one client1 has.
            if (leaseLtag == this.ltag) {
                if (this.lock.availablePermits() != 0) {
                    throw new IllegalMonitorStateException("lock should have no permits available");
                }

                this.ltag += 1;

                retVal = true;
                ltag = this.ltag;
                this.lock.release();
                this.notifyAll();
            }
        }

        return new Tuple<>(retVal, ltag);
    }
}
