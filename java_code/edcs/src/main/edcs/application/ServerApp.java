package main.edcs.application;

import main.edcs.project.GlobalVariables;
import main.edcs.project.Server;
import main.edcs.project.Tuple;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class ServerApp {
    public static void main( String[] args ) throws IOException {
        int serverIndex = parseArguments(args);
        if (serverIndex == -1) {
            printUsage();
            System.exit(0);
        }

        ServerApp.startServerProcess(serverIndex);
    }

    private static int parseArguments(String[] args) {
        if (args.length != 2 || !args[0].equals("-server")) {
            return -1;
        }

        try {
            return Integer.parseInt(args[1]);
        } catch (NumberFormatException e) {
            System.err.println("Invalid server index provided.");
            return -1;
        }
    }

    private static void printUsage() {
        System.out.println("Usage: java -jar server-app.jar -server <SERVER_INDEX>");
        System.out.println("Start a server process");
        System.out.println();
        System.out.println("Options:");
        System.out.println("  -server <SERVER_INDEX>   The index of the server in the list of servers");
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
