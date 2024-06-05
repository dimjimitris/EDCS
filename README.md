# EDCS WUT Project

## Authors

Dimitrios Georgousis (K-7729)
Gabriel Paic

## Description

Topic: 13 write – update. Implement distributed memory with read and write access, using write-update protocol.
We present a concept design for the above distributed system which reflects our current vision of implementation. The aim of the project is educational.

## Installation

Clone this repo. And follow [usage](#usage) instructions.

## Environment
Windows (11 Pro 64-bit):
```powershell
PS > java -version
java version "1.8.0_411"
Java(TM) SE Runtime Environment (build 1.8.0_411-b09)
Java HotSpot(TM) Client VM (build 25.411-b09, mixed mode, sharing)
PS > python --version
Python 3.12.1
PS > pip show jpype1
Name: JPype1
Version: 1.5.0
Summary: A Python to Java bridge.
Home-page: https://github.com/jpype-project/jpype
Author: Steve Menard
Author-email: devilwolf@users.sourceforge.net
License: License :: OSI Approved :: Apache Software License
Location: <somewhere>
Requires: packaging
Required-by:
```
Linux:
```bash
$ lsb_release -a
No LSB modules are available.
Distributor ID: Ubuntu
Description:    Ubuntu 22.04.4 LTS
Release:        22.04
Codename:       jammy
$ java -version
openjdk version "11.0.22" 2024-01-16
OpenJDK Runtime Environment (build 11.0.22+7-post-Ubuntu-0ubuntu222.04.1)
OpenJDK 64-Bit Server VM (build 11.0.22+7-post-Ubuntu-0ubuntu222.04.1, mixed mode, sharing)
$ python3 --version
Python 3.10.12
$ pip show jpype1
Name: JPype1
Version: 1.5.0
Summary: A Python to Java bridge.
Home-page: https://github.com/jpype-project/jpype
Author: Steve Menard
Author-email: devilwolf@users.sourceforge.net
License: License :: OSI Approved :: Apache Software License
Location: <somewhere>
Requires: packaging
Required-by:
```
## Project Structure

```bash
$ tree
├── java_code
│   └── edcs
│       ├── edcs.iml
│       ├── out
│       │   ├── artifacts
│       │   │   ├── client_app_jar
│       │   │   │   └── client-app.jar
│       │   │   └── server_app_jar
│       │   │       └── server-app.jar
│       └── src
│           └── main
│               └── edcs
│                   ├── application
│                   │   ├── ClientApp.java
│                   │   └── ServerApp.java
│                   └── project
│                       ├── Cache.java
│                       ├── ClientLogic.java
│                       ├── CommUtils.java
│                       ├── GlobalVariables.java
│                       ├── LockItem.java
│                       ├── MemoryItem.java
│                       ├── MemoryManager.java
│                       ├── Server.java
│                       ├── TimeUtils.java
│                       ├── Tuple.java
│                       └── Tuple2.java
├── python_code
    ├── cache.py
    ├── client.py
    ├── client_logic.py
    ├── client_wrapper.py
    ├── comm_utils.py
    ├── global_variables.py
    ├── memory_manager.py
    ├── memory_primitives.py
    ├── server.py
    ├── test.py
    ├── test_concurrent.py
    ├── test_forgotten_locks.py
    ├── test_times.py
    └── time_utils.py
```
We would advise you to first look at the python code and then the Java implementation. Commenting in the Python version is much more verbose. Nonetheless, important details are commented in the Java version too.

Explanations:

- `global_variables`: loads environmental variables from .env file
- `time_utils`: provides an interface used for timestamping write and lock tags in our code.
- `comm_utils`: implements the communication protocol between our TCP sockets (a message is sent in two parts: The first part is of fixed length and contains information about the length of the actual message and then the actual mesasge is sent)
- `memory_primitives`: contains `memory items` and `lock items` which are used by `memory_manager` and `cache` for storing and synchronization.
- `memory_manager`: handles the main memory accesses to a Node's memory addresses.
- `server`: uses a memory manager and a cache object internally. `Server` is synonymous to `Node` in this project. It also handles communication with clients by accepting their connections and serving their requests but may also make requests to other servers through the `_get_from_remote()` method.
- `client_logic`: wraps the requests that a client may send to a server in a more user friendly way
- `client_wrapper`: allows one to wrap a Python class around either a Python `client_logic` object or a Java `ClientLogic` object. This class is used in testing and allows testing both Python and Java clients.
- `client`: simple client that connects to a server and performs operations inputted by the user
- `test*`: these files can be used for testing various behaviours of our system
- `ClientApp`: same as the Python `client` but for the Java implementation
- `ServerApp`: implements the main method of the Python `server` module, but in Java.

The Java code was written as an IntelliJ IDEA Java Project. The Java jar files which are used for servers and clients (see [usage](#usage)) were produces as Artifacts through IntelliJ in case you wish to reproduce them.

## Usage

.env files
```.env
HEADER_LENGTH=64
FORMAT=utf-8
CONNECTION_TIMEOUT=10
LEASE_TIMEOUT=8
SERVERS=192.168.160.1:6000,192.168.170.134:6001,192.168.170.134:6002
MEMORY_SIZE=300
CACHE_SIZE=50
MAXIMUM_CONNECTIONS=400
SUCCESS=0
ERROR=1
INVALID_ADDRESS=2
INVALID_OPERATION=3
JAVA_JAR_FILE=../java_code/edcs/out/artifacts/server_app_jar/server-app.jar
```
A `.env` file such as this must be present in the directory from which we run Servers or clients. The `JAVA_JAR_FILE` variable is used when performing tests using the Java classes instead of the Python ones.

As mentioned in the `concept` the Servers' addresses and memory space are static and are set by the above environment variables.

Python code:
```bash
/python_code$ python3 server.py -h
usage: server.py [-h] -server SERVER

Start a server process

options:
  -h, --help      show this help message and exit
  -server SERVER  The index of the server in the list of servers
/python_code$ python3 client.py -h
usage: client.py [-h] [-server SERVER]

Client to connect to a memory server

options:
  -h, --help      show this help message and exit
  -server SERVER  The index of the server in the list of servers, if this
                  option is missing connect to a random server
```

Java code:
```bash
/EDCS/java_code/edcs/out/artifacts/server_app_jar$ java -jar server-app.jar -h
Usage: java -jar server-app.jar -server <SERVER_INDEX>
Start a server process

Options:
  -server <SERVER_INDEX>   The index of the server in the list of servers
/EDCS/java_code/edcs/out/artifacts/client_app_jar$ java -jar client-app.jar -h
Usage: java -jar client-app.jar -server <SERVER_INDEX>
Start a client process which connect to a memory server

Options:
  -server <SERVER_INDEX>   The index of the server in the list of servers, if this option is missing connect to a random server
```

In general, it is advised and expected that you have the Servers up and running before connecting clients to them.