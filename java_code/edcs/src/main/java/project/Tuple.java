package main.java.project;

public class Tuple<X, Y> {
    private final X x;
    private final Y y;

    public Tuple(X x, Y y) {
        this.x = x;
        this.y = y;
    }

    public X getX() {
        return this.x;
    }

    public Y getY() {
        return this.y;
    }

    public boolean equals(Tuple<X, Y> tuple) {
        return this.x.equals(tuple.x) && this.y.equals(tuple.y);
    }

    public String toString() {
        return "(" + this.x + ", " + this.y + ")";
    }

}