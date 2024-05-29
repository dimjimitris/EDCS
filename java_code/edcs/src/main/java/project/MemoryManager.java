package main.java.project;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MemoryManager {
    private Map<Integer, MemoryItem> memory;
    private Map<Integer, LockItem> locks;
    private Map<Integer, List<Tuple<String, Integer>>> copyHolders;
    private Tuple<Integer, Integer> memoryRange;

    public MemoryManager(Tuple<Integer, Integer> memoryRange) {
        this.memory = new HashMap<>();
        this.locks = new HashMap<>();
        this.copyHolders = new HashMap<>();
        this.memoryRange = memoryRange;

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
        
        Tuple<Boolean, Long> lockResult = lockItem.acquireLock(leaseSeconds);
        
        return new Tuple2<>(lockResult.getX(), lockResult.getY(), this.memory.get(address).getWtag());
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
