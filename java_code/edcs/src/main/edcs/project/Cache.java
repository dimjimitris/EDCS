package main.edcs.project;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

public class Cache {

    private int cacheSize;
    protected ConcurrentHashMap<Integer, Integer> keyMap;
    private ConcurrentHashMap<Integer, MemoryItem> cache;
    private ConcurrentHashMap<Integer, Lock> locks;

    public Cache(int cacheSize) {
        this.cacheSize = cacheSize;
        this.keyMap = new ConcurrentHashMap<>(cacheSize);
        this.cache = new ConcurrentHashMap<>(cacheSize);
        this.locks = new ConcurrentHashMap<>(cacheSize);

        for (int i = 0; i < cacheSize; i++) {
            keyMap.put(i, -1);
            cache.put(i, new MemoryItem(null, "C", -1));
            locks.put(i, new ReentrantLock());
        }
    }

    /*
    Description: Read from cache without synchronization.
    Used in the dumpcache functionality, which is called just for
    debugging/checking purposes.
     */
    public MemoryItem readNoSync(int memoryAddress) {
        int key = memoryAddress % cacheSize;
        if (memoryAddress != keyMap.get(key)) {
            return null;
        }
        return cache.get(key);
    }

    // Description: Read from cache with synchronization.
    public MemoryItem read(int memoryAddress) {
        synchronized (this.getLock(memoryAddress)) {
            return readNoSync(memoryAddress);
        }
    }

    // Description: Write to cache with synchronization.
    public MemoryItem write(int memoryAddress, Object data, String status, long wtag) {
        synchronized (this.getLock(memoryAddress)) {
            int key = memoryAddress % cacheSize;
            MemoryItem memoryItem = cache.get(key);
            if (memoryAddress == keyMap.get(key)) {
                memoryItem.setData(data);
                memoryItem.setStatus(status);
                memoryItem.setWtag(wtag);
            } else {
                keyMap.put(key, memoryAddress);
                memoryItem = new MemoryItem(data, status, wtag);
                cache.put(key, memoryItem);
            }
            return memoryItem;
        }
    }

    // Description: Remove an item from the cache with synchronization.
    public void remove(int memoryAddress) {
        synchronized (this.getLock(memoryAddress)) {
            int key = memoryAddress % cacheSize;
            if (memoryAddress == keyMap.get(key)) {
                keyMap.put(key, -1);
                cache.put(key, new MemoryItem(null, "C", -1));
            }
        }
    }

    // Description: Get the lock for a given memory address.
    public Lock getLock(int memoryAddress) {
        int key = memoryAddress % cacheSize;
        return locks.get(key);
    }
}