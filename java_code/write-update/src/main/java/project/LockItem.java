package project;

import java.util.Timer;
import java.util.TimerTask;
import java.util.concurrent.Semaphore;

public class LockItem {
    private Semaphore lock;
    private long ltag;

    public LockItem() {
        this.lock = new Semaphore(1);
        this.ltag = TimeUtils.getTime();
    }

    public synchronized Tuple<Boolean, Long> acquireLock(Long leaseSeconds) throws InterruptedException {
        boolean retVal = false;
        long ltag = -1;

        while (!this.lock.tryAcquire()) {
            this.wait();
        }
        retVal = true;
        this.ltag += 1;
        ltag = this.ltag;

        if (leaseSeconds != null) {
            long finalLtag = ltag;
            new Timer().schedule(new TimerTask() {
                @Override
                public void run() {
                    releaseLock(finalLtag);
                }
            }, leaseSeconds * 1000L);
        }
        return new Tuple<>(retVal, ltag);
    }

    public synchronized Tuple<Boolean, Long> releaseLock(long leaseLtag) {
        boolean retVal = false;
        long ltag = this.ltag;

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

        return new Tuple<>(retVal, ltag);
    }
}
