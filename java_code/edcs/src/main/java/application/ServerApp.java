package main.java.application;

import main.java.project.GlobalVariables;
import main.java.project.Server;
import main.java.project.Tuple;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class ServerApp {
    public static void main( String[] args ) throws IOException {
        int serverIndex = -1;
        if (args.length > 0 && args[0].startsWith("-server")) {
            try {
                serverIndex = Integer.parseInt(args[1]);
            } catch (Exception e) {
                System.out.println("Invalid server index provided.");
                return;
            }
        }

        ServerApp.startServerProcess(serverIndex);
    }

    private static void startServerProcess(int serverIndex) throws IOException {
        int memorySize = GlobalVariables.MEMORY_SIZE;
        int serverCount = GlobalVariables.SERVERS.toArray().length;
        int serverMemorySize = memorySize / serverCount;
        List<Tuple<Integer, Integer>> memoryRanges = new ArrayList<>();

        for(int i = 0; i < serverCount; i++) {
            memoryRanges.add(new Tuple<>(i * serverMemorySize, (i + 1) * serverMemorySize));
        }
        List<Tuple<String, Integer>> netAddresses = GlobalVariables.SERVERS;
        Tuple<String, Integer> netAddress = netAddresses.get(serverIndex);
        Tuple<Integer, Integer> memoryRange = memoryRanges.get(serverIndex);
        Server server = new Server(netAddress, memoryRange, netAddresses, memoryRanges);
        server.start();
    }
}