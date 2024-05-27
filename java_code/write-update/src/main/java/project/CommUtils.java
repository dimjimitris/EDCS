package project;

import java.io.*;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

import org.json.JSONObject;

public class CommUtils {
    private static final int HEADER_LENGTH = GlobalVariables.HEADER_LENGTH;
    
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
