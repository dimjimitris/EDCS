package main.edcs.project;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.EOFException;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class Server {
    private static final int CONNECTION_TIMEOUT = GlobalVariables.CONNECTION_TIMEOUT;
    private static final int LEASE_TIMEOUT = GlobalVariables.LEASE_TIMEOUT;
    private static final int CACHE_SIZE = GlobalVariables.CACHE_SIZE;
    private static final int MAXIMUM_CONNECTIONS = GlobalVariables.MAXIMUM_CONNECTIONS;

    private final Tuple<String, Integer> serverAddress;
    private final Tuple<Integer, Integer> memoryRange;
    private final List<Tuple<String, Integer>> serverAddresses;
    private final List<Tuple<Integer, Integer>> memoryRanges;
    private final MemoryManager memoryManager;
    private final Cache sharedMemory;

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
        this.sharedMemory = new Cache(CACHE_SIZE);
    }

    // start the server and listen for incoming connections from clients
    public void start() {
        try (ServerSocket serverSocket = new ServerSocket()) {
            serverSocket.setReuseAddress(true);
            serverSocket.bind(new InetSocketAddress(serverAddress.getX(), serverAddress.getY()), MAXIMUM_CONNECTIONS);

            logMsg("[LISTENING] Server is listening on " + serverAddress);

            while (true) {
                // accept new connection
                // and create a new thread to handle the client
                // this allows for multiple clients to connect to the server
                // at the same time
                Socket clientSocket = serverSocket.accept();
                Thread thread = new Thread(() -> {
                    handleClient(clientSocket);
                });
                thread.start();
                // Thread.activeCount() - 2 because the main threa and the thread from the Timer() in the MemoryManager
                // are also counted as active threads. Sometimes, this result might still not be
                // accurate because we might have lock-leasing threads that are still active
                // but of course do not count as active connections.
                logMsg("[ACTIVE CONNECTIONS] Active connections: " + (Thread.activeCount() - 2));
            }
        } catch (IOException e) {
            e.printStackTrace();
            logMsg("[LISTENING] Server failed to listen on " + serverAddress);
        }
    }

    // handle a client connection by receiving messages from the client and
    // sending back the appropriate responses
    private void handleClient(Socket clientSocket) {
        InetSocketAddress socketAddress = (InetSocketAddress) clientSocket.getRemoteSocketAddress();
        String IP = socketAddress.getAddress().getHostAddress();
        int port = socketAddress.getPort();
        Tuple<String, Integer> clientAddress = new Tuple<>(IP, port);

        logMsg("[NEW CONNECTION] " + clientAddress + " connected.");
        boolean connected = true;

        // keep the connection open until the client sends a disconnect message
        // or communication errors occur
        while (connected) {
            JSONObject returnData = null;
            JSONObject message = null;

            try {
                message = CommUtils.recMsg(clientSocket);
            } catch (EOFException e) {
                logMsg("[ERROR RECEIVING] server " + serverAddress + ", client " + clientAddress + ", message " + message + ": " + e.getMessage());
                e.printStackTrace();
                break;
            } catch (IOException e) {
                logMsg("[ERROR RECEIVING] server " + serverAddress + ", client " + clientAddress + ": " + e.getMessage());
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
                case "serve_dump_cache":
                    returnData = serveDumpCache(clientAddress);
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
                logMsg("[ERROR SENDING] server " + serverAddress + ", client " + clientAddress + ": " + e.getMessage());
                e.printStackTrace();
                break;
            }
        }
        logMsg("[DISCONNECTED] server " + serverAddress + ", client " + clientAddress + ".");
        try {
            clientSocket.close();
        } catch (IOException e) {
            e.printStackTrace();
            logMsg("[ERROR CLOSING] server " + serverAddress + ", client " + clientAddress + ": " + e.getMessage());
        }
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

    /*
    Description:
    - Handle a read request from a client
    - If the memory address is in the server's memory range, the server
    reads the data from its memory and sends it back to the client
    - If the memory address is not in the server's memory range, the server
    forwards the request to the appropriate server

    We should explain the cascade parameter: if cascade is True, the server
    will forward the request if it doesn't find it locally. If cascade is False,
    the server will return an error if it doesn't find the memory address locally.

    Clients outside the system are setup to make requests with cascade=True.

    Thus, we have the following behaviour:
    cascade=true, address is local: outside client made a request to the server that owns the memory address
    cascade=true, address is not local: outside client made a request to a server that doesn't own the memory address
    cascade=false, address is local: inside client (another server) made a request to the server that owns the memory address
    cascade=false, address is not local: this is the most interesting one and it should never happen. It occurs when a server
    wants to find a memory address that is not local to it. This server requests the address from the server that it thinks owns
    the address, but that server doesn't have the memory address either. Our system is setup such that all servers should know
    which server has what memory addresses, thus this should never happen.
    * */
    public JSONObject serveRead(
            Tuple<String, Integer> clientAddress,
            String copyHolderIP,
            int copyHolderPort,
            int memoryAddress,
            boolean cascade,
            int leaseTimeout
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
            // if the memory address is in the server's memory range
            // read the data from the server's memory and send it back to the client
            // we use locks to ensure atomicity
            MemoryItem data = new MemoryItem("missing", "I", -1);
            long ltag = -1;
            try {
                Tuple2<Boolean, Long, Long> releaseValue = memoryManager.acquireLock(memoryAddress, null);
                boolean retVal = releaseValue.getX();
                ltag = releaseValue.getY();
                long wtag = releaseValue.getZ();

                if (!retVal) {
                    JSONObject response = new JSONObject();
                    response.put("status", GlobalVariables.ERROR);
                    response.put("message", "Failed to acquire lock");
                    return response;
                }

                // cascade=false means this should be the server that owns the memory address
                // and the copyholder address should be from another server and not an outside client
                // thus, we add the copy holder to the memory address
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
            logMsg("[READ RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);
            return response;
        }

        // if the memory address is in the server's shared cache
        // read the data from the shared cache and send it back to the client
        // we request a lock from the server that owns the memory address
        // we compare the wtags (last write tags) to make sure that the cached data is up-to-date
        MemoryItem memoryItem = sharedMemory.read(memoryAddress);

        if (memoryItem != null) {
           JSONObject acLockVal = serveAcquireLock(serverAddress, memoryAddress, leaseTimeout, true);
            if (acLockVal.getInt("status") != GlobalVariables.SUCCESS) {
                sharedMemory.remove(memoryAddress);
                return acLockVal;
            }

            if (acLockVal.getLong("wtag") == memoryItem.getWtag()) {
                JSONObject relLockVal = serveReleaseLock(serverAddress, memoryAddress, acLockVal.getLong("ltag"),true);

                if (relLockVal.getInt("status") != GlobalVariables.SUCCESS) {
                    sharedMemory.remove(memoryAddress);
                    return relLockVal;
                }

                if (relLockVal.getLong("wtag") != memoryItem.getWtag()) {
                    // stale data in cache, fetch from server
                    sharedMemory.remove(memoryAddress);
                    return serveRead(clientAddress, copyHolderIP, copyHolderPort, memoryAddress, cascade);
                }

                JSONObject response = new JSONObject();
                response.put("status", GlobalVariables.SUCCESS);
                response.put("message", "read successful");
                response.put("data", memoryItem.getData() == null ? JSONObject.NULL : memoryItem.getData());
                response.put("istatus", memoryItem.getStatus());
                response.put("wtag", memoryItem.getWtag());
                response.put("ltag", acLockVal.getLong("ltag"));
                logMsg("[READ RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);
                return response;
            }
            else {
                // stale data in cache, fetch from server
                sharedMemory.remove(memoryAddress);

                JSONObject relLockVal = serveReleaseLock(serverAddress, memoryAddress, acLockVal.getLong("ltag"),true);

                if (relLockVal.getInt("status") != GlobalVariables.SUCCESS) {
                    return relLockVal;
                }

                return serveRead(clientAddress, copyHolderIP, copyHolderPort, memoryAddress, cascade);
            }
        }

        if (!cascade) { // this should never happen (see explanation above)
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Read host address " + hostServer + "is not the server address " + serverAddress);
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

        // if requested from remote server, update shared cache
        if (response.getInt("status") == GlobalVariables.SUCCESS) {
            sharedMemory.write(
                    memoryAddress,
                    response.get("data"),
                    response.getString("istatus"),
                    response.getLong("wtag"));

        }

        return response;
    }

    /*
    Description:
    - Handle a write request from a client
    - If the memory address is in the server's memory range, the server
    writes the data to its memory and sends back a success message to the client.
    The server also sends updates to all copyholders of the memory address.
    This is the main implementation of the write-update protocol.

    - If the memory address is not in the server's memory range, the server
    forwards the request to the appropriate server
    * */
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

                if (!retVal) {
                    JSONObject response = new JSONObject();
                    response.put("status", GlobalVariables.ERROR);
                    response.put("message", "Failed to acquire lock");
                    return response;
                }

                // cascade=false means this should be the server that owns the memory address
                // and the copyholder address should be from another server and not an outside client
                // thus, we add the copy holder to the memory address
                if (!cascade && !copyHolder.equals(hostServer)) {
                    memoryManager.addCopyHolder(memoryAddress, copyHolder);
                }
                memoryManager.writeMemory(memoryAddress, data);
                // update shared copies in the system, if they exist!
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
            logMsg("[WRITE RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);
            return response;
        }

        if (!cascade) { // this should never happen (see explanation above)
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Write host address " + hostServer + "is not the server address " + serverAddress);
            return response;
        }

        // if the memory address is not in the server's memory range
        // forward the request to the appropriate server
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

    // serveAcquireLock and serveReleaseLock are used to acquire and release locks
    // they have very similar build to serveRead and serveWrite

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
                Tuple2<Boolean, Long, Long> releaseValue = memoryManager.acquireLock(memoryAddress, (long) leaseTimeout);
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
            logMsg("[ACQUIRE LOCK RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);
            return response;
        }

        if (!cascade) {
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Lock host address " + hostServer + "is not the server address " + serverAddress);
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
            logMsg("[RELEASE LOCK RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);
            return response;
        }

        if (!cascade) {
            JSONObject response = new JSONObject();
            response.put("status", GlobalVariables.ERROR);
            response.put("message", "Lock host address " + hostServer + "is not the server address " + serverAddress);
            return response;
        }

        JSONArray args = new JSONArray();
        args.put(memoryAddress);
        args.put(ltag);
        args.put(false);
        return getFromRemote(clientAddress, memoryAddress, hostServer, "serve_release_lock", args, "RELEASE LOCK");
    }

    /*
    Description:
    - Update the local cache copy of a memory address and notify the next server in the address chain
    * */
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
            logMsg("[UPDATE CACHE RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);
            return response;
        }

        JSONObject response = new JSONObject();
        response.put("status", GlobalVariables.SUCCESS);
        response.put("message", "cache updated");
        return response;
    }

    /*
     Description:
    - Dump the server's cache, used for debugging purposes
    * */
    public JSONObject serveDumpCache(
            Tuple<String, Integer> clientAddress
    ) {
        logMsg("[DUMP CACHE REQUEST] server " + serverAddress + ", client " + clientAddress);
        JSONArray cacheItems = new JSONArray();
        for(Map.Entry<Integer, Integer> e : sharedMemory.keyMap.entrySet()) {
            int memoryAddress = e.getValue();

            if (memoryAddress < 0) {
                continue;
            }

            MemoryItem mi = sharedMemory.readNoSync(memoryAddress);

            JSONObject cacheItem = new JSONObject();
            cacheItem.put("address", memoryAddress);
            cacheItem.put("data", mi.getData() == null ? JSONObject.NULL : mi.getData());
            cacheItem.put("istatus", mi.getStatus());
            cacheItem.put("wtag", mi.getWtag());

            cacheItems.put(cacheItem);
        }
        JSONObject response = new JSONObject();
        response.put("status", GlobalVariables.SUCCESS);
        response.put("message", "cache dumped");
        response.put("cache", cacheItems);
        return response;
    }

    /*
    Description: a server starts updating shared copies of a memory address.
    The server keeps track of a copyholder address chain and instead of sending
    requests to all copyholders at once, it sends a request to the first copyholder
    in the chain and then each copyholder sends a request to the next copyholder in the chain.

    The server keeps track of the copyholder address chain and if a copyholder fails to update
    the shared copy, the server removes all copyholders after the failed copyholder in the chain (
    including the failed copyholder itself). This is done to ensure that the shared copies are
    consistent across all servers.
    * */
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
        sharedMemory.write(memoryAddress, data, status, wtag);
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
                serverAddress,
                memoryAddress,
                nextAddress,
                "serve_update_cache",
                args,
                "UPDATE CACHE"
        );

        // if the next server in the chain fails to update the shared copy
        // then this server is the first to fail and we need to update the copyholder list
        // to remove all servers after the failed server in the chain (including the failed server)
        if (response.getInt("status") != GlobalVariables.SUCCESS && !response.has("server_address")) {
            JSONArray failedServer = new JSONArray();
            failedServer.put(nextAddress.getX());
            failedServer.put(nextAddress.getY());
            response.put("server_address", failedServer);
        }
        return response;
    }

    /*
    Description:
    Wrapper function to connect to a remote server and send a message.
    It is used when our requests want to retrieve something from another server.
    * */
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

        Socket hostServerSocket = null;
        JSONObject result = null;
        try {
            hostServerSocket = connectToServer(hostServer, CONNECTION_TIMEOUT);
            CommUtils.sendMsg(hostServerSocket, obj);
            result = CommUtils.recMsg(hostServerSocket);
            logMsg("[" + logType + " RESPONSE] server " + serverAddress + ", client " + clientAddress + ", address " + memoryAddress);
        } catch (IOException e) {
            logMsg("[" + logType + " ERROR] server" + serverAddress + ", client " + clientAddress + ", address " + memoryAddress + ": " + e);
            JSONObject error = new JSONObject();
            error.put("status", GlobalVariables.ERROR);
            error.put("message", "Failed to connect to the host with error: " + e.getMessage());
            result = error;
        } finally {
            try {
                if (hostServerSocket != null) {
                    disconnectFromServer(hostServerSocket);
                }
            } catch (IOException e) {
                logMsg("[" + logType + " ERROR DISCONNECTING INTERNAL] server " + serverAddress + ", client " + clientAddress + ", memory address " + memoryAddress + ": " + e.getMessage());
            }
        }
        return result;
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
        socket.setReuseAddress(true);
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

    private static void logMsg(String msg) {
        logMsg(msg, false);
    }

    private static void logMsg(String msg, boolean datetime) {
        if (datetime) {
            msg = TimeUtils.getDatetime().toString() + msg;
        }
        System.out.println(msg);
    }
}
