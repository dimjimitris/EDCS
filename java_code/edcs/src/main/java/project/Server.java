package main.java.project;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.EOFException;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class Server {
    private static final int CONNECTION_TIMEOUT = GlobalVariables.CONNECTION_TIMEOUT;
    private static final int LEASE_TIMEOUT = GlobalVariables.LEASE_TIMEOUT;

    private Tuple<String, Integer> serverAddress;
    private Tuple<Integer, Integer> memoryRange;
    private List<Tuple<String, Integer>> serverAddresses;
    private List<Tuple<Integer, Integer>> memoryRanges;
    private MemoryManager memoryManager;
    private Map<Integer, MemoryItem> sharedMemory;

    public Server(
        Tuple<String, Integer> serverAddress,
        Tuple<Integer, Integer> memoryRange,
        List<Tuple<String, Integer>> serverAddresses,
        List<Tuple<Integer, Integer>> memoryRanges
    ) {
        this.serverAddress = serverAddress;
        this.memoryRange = memoryRange;
        this.serverAddresses = serverAddresses;
        this.memoryRanges = memoryRanges;

        this.memoryManager = new MemoryManager(this.memoryRange);
        this.sharedMemory = new HashMap<>();
    }

    public void start() throws IOException {
        ServerSocket serverSocket = null;
        try {
            serverSocket = new ServerSocket();
            serverSocket.setReuseAddress(true);
            serverSocket.bind(new InetSocketAddress(serverAddress.getX(), serverAddress.getY()));

            logMsg("[LISTENING] Server is listening on " + serverAddress.toString());

            while (true) {
                Socket clientSocket = serverSocket.accept();
                Thread thread = new Thread(() -> {
                    try {
                        handleClient(clientSocket);
                    } catch (IOException e) {
                        e.printStackTrace();
                    }
                });
                thread.start();
                logMsg("[ACTIVE CONNECTIONS] Active connections: " + (Thread.activeCount() - 1));
            }
        } catch (SocketException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        } finally {
            serverSocket.close();
        }
    }

    private void handleClient(Socket clientSocket) throws IOException {
        InetSocketAddress socketAddress = (InetSocketAddress) clientSocket.getRemoteSocketAddress();
        String IP = socketAddress.getAddress().getHostAddress();
        int port = socketAddress.getPort();
        Tuple<String, Integer> clientAddress = new Tuple<>(IP, port);

        logMsg("[NEW CONNECTION] " + clientAddress.toString() + " connected.");
        boolean connected = true;

        while (connected) {
            JSONObject returnData = null;
            JSONObject message = null;

            try {
                message = CommUtils.recMsg(clientSocket);
            } catch (EOFException e) {
                logMsg("[ERROR RECEIVING] server " + serverAddress.toString() + ", client " + clientAddress.toString() + ", message " + message + ": " + e.getMessage());
                e.printStackTrace();
                break;
            } catch (IOException e) {
                logMsg("[ERROR RECEIVING] server " + serverAddress.toString() + ", client " + clientAddress.toString() + ": " + e.getMessage());
                e.printStackTrace();
                break;
            }

            if (message == null) {
                continue;
            }

            String type = message.getString("type");
            JSONArray args = message.optJSONArray("args");

            switch (type) {
                case "disconnect":
                    connected = false;
                    returnData = new JSONObject();
                    returnData.put("status", GlobalVariables.SUCCESS);
                    returnData.put("message", "disconnected");
                    break;
                case "serve_read":
                    returnData = serveRead(clientAddress, args.getString(0), args.getInt(1), args.getInt(2), args.getBoolean(3));
                    break;
                case "serve_write":
                    returnData = serveWrite(clientAddress, args.getString(0), args.getInt(1), args.getInt(2), args.get(3), args.getBoolean(4));
                    break;
                case "serve_acquire_lock":
                    returnData = serveAcquireLock(clientAddress, args.getInt(0), args.getInt(1), args.getBoolean(2));
                    break;
                case "serve_release_lock":
                    returnData = serveReleaseLock(clientAddress, args.getInt(0), args.getLong(1), args.getBoolean(2));
                    break;
                case "serve_update_cache":
                    returnData = serveUpdateCache(clientAddress, args.getJSONArray(0), args.getInt(1), args.get(2), args.getString(3), args.getLong(4));
                    break;
                default:
                    returnData = new JSONObject();
                    returnData.put("status", GlobalVariables.INVALID_OPERATION);
                    returnData.put("message", "invalid message type");
                    break;
            }

            try {
                CommUtils.sendMsg(clientSocket, returnData);
            } catch (IOException e) {
                logMsg("[ERROR SENDING] server " + serverAddress.toString() + ", client " + clientAddress.toString() + ": " + e.getMessage());
                e.printStackTrace();
                break;
            }
        }
        logMsg("[DISCONNECTED] server " + serverAddress + ", client " + clientAddress + ".");
        clientSocket.close();

    }

    public JSONObject serveRead(
            Tuple<String, Integer> clientAddress,
            String copyHolderIP,
            int copyHolderPort,
            int memoryAddress,
            boolean cascade
    ) {
        return serveRead(
          clientAddress,
          copyHolderIP,
          copyHolderPort,
          memoryAddress,
          cascade,
          LEASE_TIMEOUT
        );
    }

    public JSONObject serveRead(
            Tuple<String, Integer> clientAddress,
            String copyHolderIP,
            int copyHolderPort,
            int memoryAddress,
            boolean cascade,
            int leastTimeout
    ) {
        Tuple<String, Integer> copyHolder = new Tuple<>(copyHolderIP, copyHolderPort);

        logMsg("[READ REQUEST] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);

        Tuple<String, Integer> hostServer = getServerAddress(memoryAddress);
        if (hostServer == null) {
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Memory address out of range");
            return response;
        }

        if (hostServer.equals(serverAddress)) {
            MemoryItem data = new MemoryItem("missing", "I", -1);
            long ltag = -1;
            try {
                Tuple2<Boolean, Long, Long> releaseValue = memoryManager.acquireLock(memoryAddress, null);
                boolean retVal = releaseValue.getX();
                ltag = releaseValue.getY();
                long wtag = releaseValue.getZ();

                if (!retVal || ltag == -1 || wtag == -1) {
                    JSONObject response = new JSONObject();
                    response.put("status", GlobalVariables.ERROR);
                    response.put("message", "Failed to acquire lock");
                    return response;
                }

                if (!cascade && !copyHolder.equals(hostServer)) {
                    memoryManager.addCopyHolder(memoryAddress, copyHolder);
                }

                data = memoryManager.readMemory(memoryAddress);
            } catch (InterruptedException e) {
                e.printStackTrace();
            } finally {
                memoryManager.releaseLock(memoryAddress, ltag);
            }
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.SUCCESS);
            response.put("message", "read successful");
            response.put("data", data.getData() == null ? JSONObject.NULL : data.getData());
            response.put("istatus", data.getStatus());
            response.put("wtag", data.getWtag());
            response.put("ltag", ltag);
            logMsg("[READ RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress + ", response " + response);
            return response;
        }
        if (sharedMemory.containsKey(memoryAddress)) {
            JSONObject acLockVal = serveAcquireLock(serverAddress, memoryAddress, leastTimeout, true);
            if (acLockVal.getInt("status") != GlobalVariables.SUCCESS) {
                return acLockVal;
            }
            if (acLockVal.getLong("wtag") == sharedMemory.get(memoryAddress).getWtag()) {
                MemoryItem data = sharedMemory.get(memoryAddress);

                JSONObject relLockVal = serveReleaseLock(serverAddress, memoryAddress, acLockVal.getLong("ltag"),true);

                if (relLockVal.getInt("status") != GlobalVariables.SUCCESS) {
                    sharedMemory.remove(memoryAddress);
                    return relLockVal;
                }

                if (relLockVal.getLong("wtag") != sharedMemory.get(memoryAddress).getWtag()) {
                    sharedMemory.remove(memoryAddress);
                    return serveRead(clientAddress, copyHolderIP, copyHolderPort, memoryAddress, cascade);
                }

                JSONObject response = new JSONObject();
                response.put("status", GlobalVariables.SUCCESS);
                response.put("message", "read successful");
                response.put("data", data.getData() == null ? JSONObject.NULL : data.getData());
                response.put("istatus", data.getStatus());
                response.put("wtag", data.getWtag());
                response.put("ltag", acLockVal.getLong("ltag"));
                logMsg("[READ RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress + ", response " + response);
                return response;
            }
            else {
                sharedMemory.remove(memoryAddress);
                return serveRead(clientAddress, copyHolderIP, copyHolderPort, memoryAddress, cascade);
            }
        }

        if (!cascade) {
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Lock host address " + hostServer.toString() + "is not the server address " + serverAddress.toString());
            return response;
        }

        String IP = serverAddress.getX();
        int port = serverAddress.getY();

        JSONArray args = new JSONArray();
        args.put(IP);
        args.put(port);
        args.put(memoryAddress);
        args.put(false);

        JSONObject response = getFromRemote(
                clientAddress,
                memoryAddress,
                hostServer,
                "serve_read",
                args,
                "READ");

        if (response.getInt("status") == GlobalVariables.SUCCESS) {
            sharedMemory.put(
                    memoryAddress,
                    new MemoryItem(
                            response.get("data"),
                            response.getString("istatus"),
                            response.getLong("wtag")));
        }

        return response;
    }

    public JSONObject serveWrite(
            Tuple<String, Integer> clientAddress,
            String copyHolderIP,
            int copyHolderPort,
            int memoryAddress,
            Object data,
            boolean cascade
    ) {
        Tuple<String, Integer> copyHolder = new Tuple<>(copyHolderIP, copyHolderPort);

        logMsg("[WRITE REQUEST] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);

        Tuple<String, Integer> hostServer = getServerAddress(memoryAddress);
        if (hostServer == null) {
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Memory address out of range");
            return response;
        }

        if (hostServer.equals(serverAddress)) {
            long ltag = -1;
            try {
                Tuple2<Boolean, Long, Long> releaseValue = memoryManager.acquireLock(memoryAddress, null);
                boolean retVal = releaseValue.getX();
                ltag = releaseValue.getY();
                long wtag = releaseValue.getZ();

                if (!retVal || ltag == -1 || wtag == -1) {
                    JSONObject response = new JSONObject();
                    response.put("status", GlobalVariables.ERROR);
                    response.put("message", "Failed to acquire lock");
                    return response;
                }
                if (!cascade && !copyHolder.equals(hostServer)) {
                    memoryManager.addCopyHolder(memoryAddress, copyHolder);
                }
                memoryManager.writeMemory(memoryAddress, data);

                if (memoryManager.readMemory(memoryAddress).getStatus().equals("S")) {
                    updateSharedCopies(clientAddress, memoryAddress);
                }

            } catch (InterruptedException e) {
                e.printStackTrace();
            } finally {
                memoryManager.releaseLock(memoryAddress, ltag);
            }
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.SUCCESS);
            response.put("message", "write successful");
            logMsg("[WRITE RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress + ", response " + response);
            return response;
        }

        if (!cascade) {
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Lock host address " + hostServer.toString() + "is not the server address " + serverAddress.toString());
            return response;
        }

        String IP = serverAddress.getX();
        int port = serverAddress.getY();

        JSONArray args = new JSONArray();
        args.put(IP);
        args.put(port);
        args.put(memoryAddress);
        args.put(data);
        args.put(false);
        return getFromRemote(
                clientAddress,
                memoryAddress,
                hostServer,
                "serve_write",
                args,
                "WRITE");
    }

    public JSONObject serveAcquireLock(
            Tuple<String, Integer> clientAddress,
            int memoryAddress,
            int leaseTimeout,
            boolean cascade
    ) {
        logMsg("[ACQUIRE LOCK REQUEST] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);

        Tuple<String, Integer> hostServer = getServerAddress(memoryAddress);
        if (hostServer == null) {
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Memory address out of range");
            return response;
        }

        if (hostServer.equals(serverAddress)) {
            JSONObject response = new JSONObject();
            try {
                Tuple2<Boolean, Long, Long> releaseValue = memoryManager.acquireLock(memoryAddress, null);
                boolean retVal = releaseValue.getX();
                long ltag = releaseValue.getY();
                long wtag = releaseValue.getZ();

                if (retVal) {
                    response.put("status", GlobalVariables.SUCCESS);
                    response.put("message", "lock acquired");
                    response.put("ret_val", retVal);
                    response.put("ltag", ltag);
                    response.put("wtag", wtag);
                } else{
                    response.put("status", GlobalVariables.ERROR);
                    response.put("message", "lock not acquired");
                }
            } catch (InterruptedException e) {
                response.put("status", GlobalVariables.ERROR);
                response.put("message", "Failed to acquire lock with error: " + e.getMessage());
            }
            logMsg("[ACQUIRE LOCK RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress + ", response " + response);
            return response;
        }

        if (!cascade) {
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Lock host address " + hostServer.toString() + "is not the server address " + serverAddress.toString());
            return response;
        }

        JSONArray args = new JSONArray();
        args.put(memoryAddress);
        args.put(leaseTimeout);
        args.put(false);
        return getFromRemote(
                clientAddress,
                memoryAddress,
                hostServer,
                "serve_acquire_lock",
                args,
                "ACQUIRE LOCK"
        );
    }

    public JSONObject serveReleaseLock(
            Tuple<String, Integer> clientAddress,
            int memoryAddress,
            Long ltag,
            boolean cascade
    ) {
        logMsg("[RELEASE LOCK REQUEST] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);

        Tuple<String, Integer> hostServer = getServerAddress(memoryAddress);
        if (hostServer == null) {
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Memory address out of range");
            return response;
        }

        if (hostServer.equals(serverAddress)) {
            Tuple2<Boolean, Long, Long> releaseValue = memoryManager.releaseLock(memoryAddress, ltag);
            boolean retVal = releaseValue.getX();
            ltag = releaseValue.getY();
            long wtag = releaseValue.getZ();
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.SUCCESS);
            response.put("ret_val", retVal);
            response.put("ltag", ltag);
            response.put("wtag", wtag);
            if (retVal) {
                response.put("message", "lock released");
            } else {
                response.put("message", "lock was already released");
            }
            logMsg("[RELEASE LOCK RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress + ", response " + response);
            return response;
        }

        if (!cascade) {
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Lock host address " + hostServer.toString() + "is not the server address " + serverAddress.toString());
            return response;
        }

        JSONArray args = new JSONArray();
        args.put(memoryAddress);
        args.put(ltag);
        args.put(false);
        return getFromRemote(clientAddress, memoryAddress, hostServer, "serve_release_lock", args, "RELEASE LOCK");
    }

    public JSONObject serveUpdateCache(
            Tuple<String, Integer> clientAddress,
            JSONArray addressChain,
            int memoryAddress,
            Object data,
            String status,
            Long wtag
    ) {
        addressChain = new JSONArray(addressChain);
        logMsg("[UPDATE CACHE REQUEST] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);

        Tuple<String, Integer> hostServer = getServerAddress(memoryAddress);
        if (hostServer == null) {
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Memory address out of range");
            return response;
        }

        if (!hostServer.equals(serverAddress)) {
            updateLocalCopy(memoryAddress, data, status, wtag);
        }

        if (!addressChain.isEmpty()) {
            JSONArray nextAddressAux = addressChain.getJSONArray(0);
            Tuple<String, Integer> nextAddress = new Tuple<>(nextAddressAux.getString(0), nextAddressAux.getInt(1));
            addressChain.remove(0);
            JSONObject response = updateNextCopy(addressChain, nextAddress, memoryAddress, data, status, wtag);
            logMsg("[UPDATE CACHE RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress + ", response " + response);
            return response;
        }

        JSONObject response = new JSONObject();
        response.put("status", GlobalVariables.SUCCESS);
        response.put("message", "cache updated");
        return response;
    }

    private void updateSharedCopies(
            Tuple<String, Integer> clientAddress,
            int memoryAddress
    ) {
        List<Tuple<String, Integer>> addressChainTuples = memoryManager.getCopyHolders(memoryAddress);

        JSONArray addressChain = new JSONArray();
        for (Tuple<String, Integer> address : addressChainTuples) {
            String host = address.getX();
            int port = address.getY();
            JSONArray item = new JSONArray();
            item.put(host);
            item.put(port);
            addressChain.put(item);
        }

        logMsg("ADDRESS CHAIN: " + addressChain);

        JSONObject updateValue = serveUpdateCache(
                clientAddress,
                addressChain,
                memoryAddress,
                memoryManager.readMemory(memoryAddress).getData(),
                memoryManager.readMemory(memoryAddress).getStatus(),
                memoryManager.readMemory(memoryAddress).getWtag()
        );

        logMsg("[UPDATE SHARED COPIES] " + updateValue);

        if (updateValue.getInt("status") != GlobalVariables.SUCCESS) {
            JSONArray failedAddressAux = updateValue.optJSONArray("server_address");
            if (failedAddressAux == null) {
                failedAddressAux = addressChain.getJSONArray(0);
            }

            logMsg("[UPDATE SHARED COPIES] failure address: " + failedAddressAux);

            Tuple<String, Integer> failedAddress = new Tuple<>(failedAddressAux.getString(0), failedAddressAux.getInt(1));

            boolean flag = false;
            for(Tuple<String, Integer> address : addressChainTuples) {
                if (address.equals(failedAddress)) {
                    flag = true;
                }

                if (flag) {
                    memoryManager.removeCopyHolder(memoryAddress, address);
                }
            }
        }

        logMsg("[UPDATE SHARED COPIES] COPY HOLDERS: " + memoryManager.getCopyHolders(memoryAddress));
    }

    private boolean updateLocalCopy(
            int memoryAddress,
            Object data,
            String status,
            Long wtag
    ) {
        sharedMemory.put(memoryAddress, new MemoryItem(data, status, wtag));
        return true;
    }

    private JSONObject updateNextCopy(
        JSONArray addressChain,
        Tuple<String, Integer> nextAddress,
        int memoryAddress,
        Object data,
        String status,
        Long wtag
        ) {

        JSONArray args = new JSONArray();
        args.put(addressChain);
        args.put(memoryAddress);
        args.put(data);
        args.put(status);
        args.put(wtag);

        JSONObject response = getFromRemote(
                null,
                memoryAddress,
                nextAddress,
                "serve_update_cache",
                args,
                "UPDATE CACHE"
        );

        if (response.getInt("status") != GlobalVariables.SUCCESS && !response.has("server_address")) {
            JSONArray failedServer = new JSONArray();
            failedServer.put(nextAddress.getX());
            failedServer.put(nextAddress.getY());
            response.put("server_address", failedServer);
        }
        return response;
    }

    private JSONObject getFromRemote(
            Tuple<String, Integer> clientAddress,
            int memoryAddress,
            Tuple<String, Integer> hostServer,
            String type,
            JSONArray args,
            String logType
    ) {
        JSONObject obj = new JSONObject();
        obj.put("type", type);
        obj.put("args", args);

        try {
            Socket hostServerSocket = new Socket();
            hostServerSocket.connect(new InetSocketAddress(hostServer.getX(), hostServer.getY()), CONNECTION_TIMEOUT);
            CommUtils.sendMsg(hostServerSocket, obj);
            JSONObject response = CommUtils.recMsg(hostServerSocket);
            disconnectFromServer(hostServerSocket);
            logMsg("[" + logType + " RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress + ", response " + response);
            return response;
        } catch (IOException e) {
            logMsg("[" + logType + " ERROR] server" + serverAddress + ", client " + clientAddress + ", address " + memoryAddress + ": " + e);
            JSONObject error = new JSONObject();
            error.put("status", GlobalVariables.ERROR);
            error.put("message", "Failed to connect to the host with error: " + e.getMessage());
            return error;
        }
    }

    private Tuple<String, Integer> getServerAddress(int memoryAddress) {
        int serverIndex = getServerIndex(memoryAddress);
        if (serverIndex == -1) {
            return null;
        }
        return serverAddresses.get(serverIndex);
    }

    private int getServerIndex(int memoryAddress) {
        for(int i = 0; i < memoryRanges.size(); i++) {
            Tuple<Integer, Integer> range = memoryRanges.get(i);
            if (memoryAddress >= range.getX() && memoryAddress < range.getY()) {
                return i;
            }
        }
        return -1;
    }

    private Socket connectToServer(Tuple<String, Integer> address, int timeout) throws IOException {
        timeout = timeout < 0 ? 0 : timeout * 1000;

        Socket socket = new Socket();
        socket.connect(new InetSocketAddress(address.getX(), address.getY()), timeout);
        // socket.setSoTimeout(0);
        return socket;
    }

    private void disconnectFromServer(Socket serverSocket) throws IOException {
        JSONObject obj = new JSONObject();
        obj.put("type", "disconnect");
        try {
            CommUtils.sendMsg(serverSocket, obj);
            CommUtils.recMsg(serverSocket);
        } catch (IOException e) {
            e.printStackTrace();
        } finally {
            // serverSocket.shutdownInput();
            // serverSocket.shutdownOutput();
            serverSocket.close();
        }
    }

    private void logMsg(String msg) {
        logMsg(msg, false);
    }

    private void logMsg(String msg, boolean datetime) {
        if (datetime) {
            msg = TimeUtils.getDatetime().toString() + msg;
        }
        System.out.println(msg);
    }
}