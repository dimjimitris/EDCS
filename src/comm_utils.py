import json
import socket

import global_variables as gv


HEADER_LENGTH =  gv.HEADER_LENGTH
FORMAT = gv.FORMAT


def receive_message(client_socket: socket.socket):
    length_message = b""
    while True:
        message_part = client_socket.recv(HEADER_LENGTH)
        if not message_part:
            break
        length_message += message_part
        if len(length_message) == HEADER_LENGTH:
            break

    message_length = int(length_message.decode(FORMAT).strip())

    message = b""
    while True:
        message_part = client_socket.recv(message_length)
        if not message_part:
            break
        message += message_part
        if len(message) == message_length:
            break

    message = message.decode(FORMAT)
    message = json.loads(message)
    return message


def send_message(client_socket: socket.socket, message):
    try:
        message = json.dumps(message).encode(FORMAT)
        send_message = f"{len(message):<{HEADER_LENGTH}}".encode(FORMAT) + message
        client_socket.sendall(send_message)
    except Exception as e:
        print(f"[ERROR] sending message: {e}")


def test():
    import threading as th

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("localhost", 5050))
    server_socket.listen()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(("localhost", 5050))

    conn, addr = server_socket.accept()

    message_to_send = {"type": "read", "address": 0}

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
