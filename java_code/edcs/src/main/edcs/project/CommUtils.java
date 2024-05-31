package main.edcs.project;

import java.io.*;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

import org.json.JSONObject;

public class CommUtils {
    private static final int HEADER_LENGTH = GlobalVariables.HEADER_LENGTH;

    /*
    Description: This function receives a message from a client socket.
    The message type is json and the message is received in two parts:
    1. The length of the message
    2. The message itself
    the message is turned into a JSONObject and returned.
    * */
    public static JSONObject recMsg(Socket clientSocket) throws EOFException, IOException {
        InputStream inputStream = clientSocket.getInputStream();
        DataInputStream dataInputStream = new DataInputStream(inputStream);
        byte[] lenMsgBytes = new byte[HEADER_LENGTH];
        dataInputStream.readFully(lenMsgBytes, 0, HEADER_LENGTH);

        String d = new String(lenMsgBytes, StandardCharsets.UTF_8).trim();
        int msgLen = Integer.parseInt(d);
        byte[] msgBytes = new byte[msgLen];
        dataInputStream.readFully(msgBytes, 0, msgLen);

        String msgString = new String(msgBytes, StandardCharsets.UTF_8);

        return new JSONObject(msgString);
    }

    /*
    Description: This function sends a message to a client socket.
    The message type is JSONObject and the message is sent in two parts:
    1. The length of the message
    2. The message itself
    * */
    public static void sendMsg(Socket clientSocket, JSONObject msg) throws IOException {
        OutputStream outputStream = clientSocket.getOutputStream();
        String msgString = msg.toString();
        byte[] msgBytes = msgString.getBytes(StandardCharsets.UTF_8);
        String header = String.format("%-" + HEADER_LENGTH + "s", msgBytes.length);
        byte[] headerBytes = header.getBytes(StandardCharsets.UTF_8);

        outputStream.write(headerBytes, 0, headerBytes.length);
        outputStream.write(msgBytes, 0, msgBytes.length);
        outputStream.flush();
    }
}
