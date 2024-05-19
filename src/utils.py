import json
import socket
import time

HEADER = 64
FORMAT = 'utf-8'

def receive_message(client_socket: socket.socket):
    try:
        message_length = client_socket.recv(HEADER).decode(FORMAT)
        if message_length:
            message_length = int(message_length)
            message = json.loads(client_socket.recv(message_length).decode(FORMAT))

            if (type(message) == dict):
                for key, value in message.items():
                    try:
                        message[key] = int(value)
                    except:
                        pass

                return message
    except Exception as e:
        print(f"[ERROR] receiving message: {e}")
        return None
    
def send_message(client_socket: socket.socket, message):
    try:
        message = json.dumps(message).encode(FORMAT)
        message_length = len(message)
        send_length = str(message_length).encode(FORMAT)
        send_length += b' ' * (HEADER - len(send_length))
        client_socket.send(send_length)
        client_socket.send(message)
    except Exception as e:
        print(f"[ERROR] sending message: {e}")

def get_time():
    #t = dt.datetime.now(dt.UTC)
    #t = t.timestamp() * 1_000_000
    #return int(round(t))
    return time.time_ns()

def test():
    import threading as th

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 5050))
    server_socket.listen()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('localhost', 5050))

    conn, addr = server_socket.accept()

    message_to_send = {
        "type": "read",
        "address": 0
    }

    def send():
        send_message(client_socket, message_to_send)

    send_thread = th.Thread(target=send)
    send_thread.start()
    
    received_message = receive_message(conn)

    client_socket.close()
    server_socket.close()

    print(f"Message to send: {message_to_send}")
    print(f"Received message: {received_message}")
    print(f"Message match: {message_to_send == received_message}")

if __name__ == "__main__":
    test()