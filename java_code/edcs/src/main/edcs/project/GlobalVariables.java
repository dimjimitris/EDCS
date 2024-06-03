package main.edcs.project;

import io.github.cdimascio.dotenv.Dotenv;

import java.util.ArrayList;
import java.util.List;

public class GlobalVariables {
    private static final Dotenv dotenv = Dotenv.load();

    public static final int HEADER_LENGTH = Integer.parseInt(dotenv.get("HEADER_LENGTH"));
    public static final String FORMAT = dotenv.get("FORMAT");

    public static final int CONNECTION_TIMEOUT = Integer.parseInt(dotenv.get("CONNECTION_TIMEOUT"));
    public static final int LEASE_TIMEOUT = Integer.parseInt(dotenv.get("LEASE_TIMEOUT"));

    public static final List<Tuple<String, Integer>> SERVERS = parseServers(dotenv.get("SERVERS"));

    public static final int MEMORY_SIZE = Integer.parseInt(dotenv.get("MEMORY_SIZE"));
    public static final int CACHE_SIZE = Integer.parseInt(dotenv.get("CACHE_SIZE"));

    public static final int SUCCESS = Integer.parseInt(dotenv.get("SUCCESS"));
    public static final int ERROR = Integer.parseInt(dotenv.get("ERROR"));
    public static final int INVALID_ADDRESS = Integer.parseInt(dotenv.get("INVALID_ADDRESS"));
    public static final int INVALID_OPERATION = Integer.parseInt(dotenv.get("INVALID_OPERATION"));

    private static List<Tuple<String, Integer>> parseServers(String servers) {
        List<Tuple<String, Integer>> serverList = new ArrayList<>();
        String[] serverArray = servers.split(",");
        for (String server : serverArray) {
            String[] parts = server.split(":");
            serverList.add(new Tuple<>(parts[0], Integer.parseInt(parts[1])));
        }
        return serverList;
    }

    public static void main(String[] args) {
        System.out.println("Header Length: " + HEADER_LENGTH);
        System.out.println("Format: " + FORMAT);
        System.out.println("Connection Timeout: " + CONNECTION_TIMEOUT);
        System.out.println("Lease Timeout: " + LEASE_TIMEOUT);
        System.out.println("Servers: " + SERVERS);
        System.out.println("Memory Size: " + MEMORY_SIZE);
        System.out.println("SUCCESS status: " + SUCCESS);
        System.out.println("ERROR status: " + ERROR);
        System.out.println("INVALID_ADDRESS status: " + INVALID_ADDRESS);
        System.out.println("INVALID_OPERATION status: " + INVALID_OPERATION);
    }
}