package main.java.project;

import java.util.HashMap;
import java.util.Map;

public class MemoryItem {
    private Object data;
    private String status;
    private Long wtag;

    public MemoryItem(Object data, String status) {
        this(data, status, TimeUtils.getTime());
    }

    public MemoryItem(Object data, String status, long wtag) {
        this.data = data;
        this.status = status;
        this.wtag = wtag;
    }

    public Object getData() {
        return this.data;
    }

    public void setData(Object data) {
        this.data = data;
    }

    public String getStatus() {
        return this.status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Long getWtag() {
        return this.wtag;
    }

    public void setWtag(Long wtag) {
        this.wtag = wtag;
    }

    public Map<String, Object> toJson() {
        Map<String, Object> jsonMap = new HashMap<>();
        
        jsonMap.put("data", this.data);
        jsonMap.put("istatus", this.status);
        jsonMap.put("wtag", this.wtag);
        
        return jsonMap;
    }

    @Override
    public String toString() {
        return "{data=" + this.data + ", status=" + this.status + "}";
    }
}
