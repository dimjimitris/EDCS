from flask import Flask, render_template, request, jsonify
import random
import jpype
from jpype import java
import global_variables as gv
import client_logic
import sys
import json

app = Flask(__name__)

# Default client logic type
CLIENT_LOGIC_TYPE = 'java'

# Check if command-line argument -type is provided and set CLIENT_LOGIC_TYPE accordingly
if len(sys.argv) > 1 and sys.argv[1] == "-type":
    if len(sys.argv) > 2:
        if sys.argv[2] in ['java', 'python']:
            CLIENT_LOGIC_TYPE = sys.argv[2]
        else:
            print("Invalid client logic type. Please choose 'java' or 'python'.")
            sys.exit(1)
    else:
        print("Client logic type argument missing. Please specify 'java' or 'python'.")
        sys.exit(1)

# Start the JVM if Java client logic is chosen
if CLIENT_LOGIC_TYPE == 'java':
    jpype.startJVM(classpath=[gv.JAVA_JAR_FILE])

    # Load the Java ClientLogic class
    ClientLogic = jpype.JClass("main.edcs.project.ClientLogic")

class ClientManager:
    def __init__(self):
        self.clients = {}

    def connect(self, client_id, server_index=None):
        server_address = random.choice(gv.SERVERS) if server_index is None else gv.SERVERS[server_index]
        if CLIENT_LOGIC_TYPE == 'java':
            client = ClientLogic(server_address[0], server_address[1])
        else:
            client = client_logic.Client(server_address)
        client.connect()
        self.clients[client_id] = client
        return f"Client {client_id} connected to server {server_address}"

    def disconnect(self, client_id):
        client = self.clients.get(client_id)
        if client:
            resp = client.disconnect()
            del self.clients[client_id]
            return self._treat_java_response(resp)
        return f"Client {client_id} not found."

    def send_command(self, client_id, command, mem_address=None, data=None, lease_tag=None):
        client = self.clients.get(client_id)
        if not client:
            return f"Client {client_id} is not connected."

        try:
            if command == "read":
                result = client.read(int(mem_address))

                return self._treat_java_response(result)

            elif command == "write":
                data = int(data) if data.isdigit() else data
                result = client.write(int(mem_address), data)

                return self._treat_java_response(result)

            elif command == "lock":
                if CLIENT_LOGIC_TYPE == 'java':
                    result = client.acquireLock(int(mem_address))
                else:
                    result = client.acquire_lock(int(mem_address))
                return self._treat_java_response(result)

            elif command == "unlock":
                if CLIENT_LOGIC_TYPE == 'java':
                    result = client.releaseLock(int(mem_address), int(lease_tag))
                else:
                    result = client.release_lock(int(mem_address), int(lease_tag))
                return self._treat_java_response(result)

            elif command == "dumpcache":
                if CLIENT_LOGIC_TYPE == 'java':
                    result = client.dumpCache()
                else:
                    result = client.dump_cache()
                return self._treat_java_response(result)

            else:
                return "Invalid command."
        except Exception as e:
            return str(e)
        
    def _treat_java_response(self, response):
        if CLIENT_LOGIC_TYPE == 'java':
            response = response.toString()
            response = str(response)
            return json.loads(response)
        return response

client_manager = ClientManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect', methods=['POST'])
def connect():
    client_id = request.form.get('client_id')
    server_index = request.form.get('server_index')
    server_index = int(server_index) if server_index else None
    response = client_manager.connect(client_id, server_index)
    return jsonify(response=response)

@app.route('/disconnect', methods=['POST'])
def disconnect():
    client_id = request.form.get('client_id')
    response = client_manager.disconnect(client_id)
    return jsonify(response=response)

@app.route('/command', methods=['POST'])
def command():
    client_id = request.form.get('client_id')
    command = request.form.get('command')
    mem_address = request.form.get('mem_address')
    data = request.form.get('data')
    lease_tag = request.form.get('lease_tag')
    response = client_manager.send_command(client_id, command, mem_address, data, lease_tag)
    return jsonify(response=response)

if __name__ == "__main__":
    app.run(debug=True)

# Shutdown the JVM if Java client logic is chosen
if CLIENT_LOGIC_TYPE == 'java':
    jpype.shutdownJVM()
