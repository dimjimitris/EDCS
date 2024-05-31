package main.edcs.project;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;


public class TimeUtils {
    // get the current UTC time in nanoseconds
    public static long getTime() {
    	Instant now = Instant.now(Clock.systemUTC());
        long seconds = now.getEpochSecond();
        long nanos = now.getNano();
        return seconds * 1_000_000_000L + nanos;
    }
    // get the current datetime in UTC
    public static LocalDateTime getDatetime() {
        return LocalDateTime.now(ZoneOffset.UTC);
    }

    public static void main(String[] args) {
        System.out.println("Current time in nanoseconds: " + getTime());
        System.out.println("Current datetime in UTC: " + getDatetime());
    }
}
