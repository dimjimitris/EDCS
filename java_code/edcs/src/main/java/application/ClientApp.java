package main.java.application;

import org.json.JSONObject;
import main.java.project.ClientLogic;
import main.java.project.GlobalVariables;
import main.java.project.Tuple;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Random;
import java.util.Scanner;

public class ClientApp {
    public static void main(String[] args) {
        // Parse command-line arguments
        int serverIndex = -1;
        if (args.length > 0 && args[0].startsWith("-server")) {
            try {
                serverIndex = Integer.parseInt(args[1]);
            } catch (Exception e) {
                System.out.println("Invalid server index provided.");
                return;
            }
        }

        ArrayList<Tuple<String, Integer>> myServers = new ArrayList<>(GlobalVariables.SERVERS);
        // Select server address
        Tuple<String, Integer> serverAddress = serverIndex == -1
                ? myServers.get(new Random().nextInt(myServers.toArray().length))
                : myServers.get(serverIndex);

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
                System.out.print("Enter command (read <address> | write <address> <data> | disconnect): ");
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
}
