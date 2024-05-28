package main.java.project;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;

public class ClientLogic {
    private Tuple<String, Integer> serverAddress;
    private Socket socket;
    public ClientLogic(Tuple<String, Integer> serverAddress) {
        this.serverAddress = serverAddress;
    }

    public void connect() throws IOException {
        socket = new Socket();
        socket.connect(
                new InetSocketAddress(serverAddress.getX(), serverAddress.getY()),
                GlobalVariables.CONNECTION_TIMEOUT * 3000
        );
    }

    public JSONObject disconnect() throws IOException {
        JSONObject msg = new JSONObject();
        msg.put("type", "disconnect");
        CommUtils.sendMsg(socket, msg);
        JSONObject resp = CommUtils.recMsg(socket);
        socket.close();
        return resp;
    }

    public JSONObject write(int memoryAddress, Object data) throws IOException {

        JSONObject msg = new JSONObject();
        msg.put("type", "serve_write");
        JSONArray args = new JSONArray();
        args.put("");
        args.put(-1);
        args.put(memoryAddress);
        args.put(data);
        args.put(true);
        msg.put("args", args);

        CommUtils.sendMsg(socket, msg);
        JSONObject resp = CommUtils.recMsg(socket);
        return resp;
    }

    public JSONObject read(int memoryAddress) throws IOException {
        JSONObject msg = new JSONObject();
        msg.put("type", "serve_read");
        JSONArray args = new JSONArray();
        args.put("");
        args.put(-1);
        args.put(memoryAddress);
        args.put(true);
        msg.put("args", args);

        CommUtils.sendMsg(socket, msg);
        JSONObject resp = CommUtils.recMsg(socket);
        return resp;
    }

    public JSONObject acquire_lock(int memoryAddress) throws IOException {
        JSONObject msg = new JSONObject();
        msg.put("type", "serve_acquire_lock");
        JSONArray args = new JSONArray();
        args.put(memoryAddress);
        args.put(GlobalVariables.LEASE_TIMEOUT);
        args.put(true);
        msg.put("args", args);

        CommUtils.sendMsg(socket, msg);
        JSONObject resp = CommUtils.recMsg(socket);
        return resp;
    }
}