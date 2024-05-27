package project;

public class MemoryRange {
	public int start;
    public int end;

    public MemoryRange(int start, int end) {
        this.start = start;
        this.end = end;
    }

    @Override
    public String toString() {
        return "(" + this.start + ", " + this.end + ")";
    }
}
