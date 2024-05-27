package project;

public class Tuple2<X, Y, Z> {
    private X x;
    private Y y;
    private Z z;
    
    public Tuple2(X x, Y y, Z z) {
        this.x = x;
        this.y = y;
        this.z = z;
    }

	public X getX() {
		return this.x;
	}

	public Y getY() {
		return this.y;
	}

	public Z getZ() {
		return this.z;
	}
}
