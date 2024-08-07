package main.edcs.project;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class MemoryManager {
    private Map<Integer, MemoryItem> memory;
    private Map<Integer, LockItem> locks;
    private Map<Integer, List<Tuple<String, Integer>>> copyHolders;
    private Tuple<Integer, Integer> memoryRange;
    private Timer lockTimer;

    public MemoryManager(Tuple<Integer, Integer> memoryRange) {
        this.memory = new ConcurrentHashMap<>();
        this.locks = new ConcurrentHashMap<>();
        this.copyHolders = new ConcurrentHashMap<>();
        this.memoryRange = memoryRange;
        // the lockTimer is basically a thread that is tasked with
        // running all the lock-lease timeout tasks that occur
        // when a remote process acquires a lock
        // This is an implementation difference compared to our python code
        this.lockTimer = new Timer();

        for(int i = this.memoryRange.getX(); i < this.memoryRange.getY(); i++) {
        	this.memory.put(i, new MemoryItem(null, "E"));
        	this.locks.put(i, new LockItem());
        	this.copyHolders.put(i, new ArrayList<>());
        }
    }

    public MemoryItem readMemory(int address) {
        return this.memory.getOrDefault(address, null);
    }

    public MemoryItem writeMemory(int address, Object data) {
        MemoryItem item = this.memory.get(address);
        
        if(item != null) {
            item.setData(data);
            item.setWtag(item.getWtag() + 1);
        }
        
        return item;
    }

    // return:
    // - retVal: true if the lock is acquired, false otherwise
    // - ltag: the lock tag
    // - wtag: the write tag
    public Tuple2<Boolean, Long, Long> acquireLock(int address, Long leaseSeconds) throws InterruptedException {
        LockItem lockItem = this.locks.get(address);
        
        if(lockItem == null) {
            return new Tuple2<>(false, (long) -1, (long) -1);
        }
        
        Tuple<Boolean, Long> lockResult = lockItem.acquireLock();
        boolean retVal = lockResult.getX();
        long ltag = lockResult.getY();

        // the lease seconds applies if the lock is acquired by a remote client
        // this client could potentially fail and keep the lock forever, thus
        // we release the lock after the lease_seconds
        if (retVal && leaseSeconds != null) {
            // class Timer is thread safe
            lockTimer.schedule(
                    new TimerTask() {
                        @Override
                        public void run() {
                            Tuple<Boolean, Long> resp = lockItem.releaseLock(ltag);
                            boolean success = resp.getX();
                            if (success) {
                                System.out.println("[LOCK TIMER] lock released for memory address: " + address);
                            }
                        }
                    }, leaseSeconds * 1000L
            );
        }

        return new Tuple2<>(retVal, ltag, this.memory.get(address).getWtag());
    }

    // return:
    // - retVal: true if the lock is released, false otherwise
    // - ltag: the lock tag
    // - wtag: the write tag
    public Tuple2<Boolean, Long, Long> releaseLock(int address, long leaseLtag) {
        LockItem lockItem = this.locks.get(address);
        
        if(lockItem == null) {
            return new Tuple2<>(false, (long) -1, (long) -1);
        }
        MemoryItem memoryItem = this.memory.get(address);
        long wtag = memoryItem.getWtag();
        Tuple<Boolean, Long> releaseResult = lockItem.releaseLock(leaseLtag);

        return new Tuple2<>(releaseResult.getX(), releaseResult.getY(), wtag);
    }

    public boolean setStatus(int address, String status) {
        MemoryItem memoryItem = this.memory.get(address);
        
        if(memoryItem == null) {
            return false;
        }
        
        memoryItem.setStatus(status);
        
        return true;
    }

    public List<Tuple<String, Integer>> getCopyHolders(int address) {
        return new ArrayList<>(this.copyHolders.getOrDefault(address, Collections.emptyList()));
    }

    // return:
    // - true: if the holder is in the copyHolders list
    public boolean addCopyHolder(int address, Tuple<String, Integer> holder) {
        List<Tuple<String, Integer>> holders = this.copyHolders.get(address);
        
        if(holders == null) {
            return false;
        }

        if (holders.contains(holder)) {
            return true;
        }
        
        holders.add(holder);
        this.memory.get(address).setStatus("S");
        
        return true;
    }

    // return:
    // - true: if the holder is not in the copyHolders list
    public boolean removeCopyHolder(int address, Tuple<String, Integer> holder) {
        List<Tuple<String, Integer>> holders = this.copyHolders.get(address);
        
        if(holders == null) {
            return false;
        }

        if (!holders.contains(holder)) {
            return true;
        }

        holders.remove(holder);
        
        if(holders.isEmpty()) {
        	this.memory.get(address).setStatus("E");
        }
        
        return true;
    }
}
