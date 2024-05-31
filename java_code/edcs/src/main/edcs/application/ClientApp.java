package main.edcs.application;

import org.json.JSONObject;
import main.edcs.project.ClientLogic;
import main.edcs.project.GlobalVariables;
import main.edcs.project.Tuple;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Random;
import java.util.Scanner;

public class ClientApp {
    public static void main(String[] args) {
        // Parse command-line arguments
        int serverIndex = parseArguments(args);
        if (serverIndex == -1) {
            printUsage();
            System.exit(0);
        }

        ArrayList<Tuple<String, Integer>> myServers = new ArrayList<>(GlobalVariables.SERVERS);
        // Select server address
        Tuple<String, Integer> serverAddress = myServers.get(serverIndex);

        // Create client and connect to the server
        ClientLogic client = new ClientLogic(serverAddress);
        try {
            client.connect();
        } catch (IOException e) {
            System.out.println("Failed to connect to the server.");
            return;
        }

        Scanner scanner = new Scanner(System.in);

        while (true) {
            try {
                System.out.print(
                        "Enter command (\n" +
                                "read <address>\n" +
                                "write <address> <data>\n" +
                                "lock <address>\n" +
                                "unlock <address> <lease tag>\n" +
                                "dumpcache | disconnect): ");
                String userInput = scanner.nextLine().trim();
                if (userInput.isEmpty()) {
                    continue;
                }

                String[] parts = userInput.split("\\s+", 3);
                String command = parts[0].toLowerCase();

                if (command.equals("read") && parts.length == 2) {
                    int memAddress = Integer.parseInt(parts[1]);
                    JSONObject result = client.read(memAddress);
                    System.out.println("Read from " + memAddress + ": " + result);

                } else if (command.equals("write") && parts.length == 3) {
                    int memAddress = Integer.parseInt(parts[1]);
                    Object data;
                    try {
                        data = Integer.parseInt(parts[2]);
                    } catch (NumberFormatException e) {
                        data = parts[2];
                    }

                    JSONObject result = client.write(memAddress, data);
                    System.out.println("Write to " + memAddress + ": " + result);

                } else if (command.equals("lock") && parts.length == 2) {
                    int memAddress = Integer.parseInt(parts[1]);
                    JSONObject result = client.acquireLock(memAddress);
                    System.out.println("Lock " + memAddress + ": " + result);
                } else if (command.equals("unlock") && parts.length == 3) {
                    int memAddress = Integer.parseInt(parts[1]);
                    long leaseTime = Long.parseLong(parts[2]);
                    JSONObject result = client.releaseLock(memAddress, leaseTime);
                    System.out.println("Unlock " + memAddress + ": " + result);
                } else if (command.equals("dumpcache")) {
                    JSONObject result = client.dumpCache();
                    System.out.println("Dump cache: " + result);
                } else if (command.equals("disconnect")) {
                    client.disconnect();
                    break;

                } else {
                    System.out.println("Invalid command. Please use read <address>, write <address> <data>, or disconnect.");
                }

            } catch (Exception e) {
                System.out.println("Error: " + e.getMessage());

                try {
                    client.disconnect();
                } catch (IOException ioException) {
                    System.out.println("Error during disconnection: " + ioException.getMessage());
                }

                boolean reconnected = false;
                int i = 0;
                for (Tuple<String, Integer> newServerAddress: GlobalVariables.SERVERS) {
                    try {
                        client = new ClientLogic(newServerAddress);
                        client.connect();
                        reconnected = true;
                        System.out.println("Reconnected to server with index: " + i + ".");
                        break;
                    } catch (IOException ioException) {
                        // Ignore and try the next server
                    }
                    i += 1;
                }

                if (!reconnected) {
                    System.out.println("Failed to reconnect to server. Exiting.");
                    break;
                }
            }
        }

        scanner.close();
    }

    private static int parseArguments(String[] args) {
        if (args.length == 0) {
            ArrayList<Tuple<String, Integer>> myServers = new ArrayList<>(GlobalVariables.SERVERS);
            return new Random().nextInt(myServers.toArray().length);
        }

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
        System.out.println("Usage: java -jar client-app.jar -server <SERVER_INDEX>");
        System.out.println("Start a client process which connect to a memory server");
        System.out.println();
        System.out.println("Options:");
        System.out.println("  -server <SERVER_INDEX>   The index of the server in the list of servers, if this option is missing connect to a random server");
    }
}
