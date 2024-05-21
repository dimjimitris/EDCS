import json
import socket

import global_variables as gv

HEADER_LENGTH = gv.HEADER_LENGTH
FORMAT = gv.FORMAT

def rec_msg(client_socket: socket.socket):
    """
    Description: This function receives a message from a client socket.
    The message type is json and the message is received in two parts:
    1. The length of the message
    2. The message itself
    json is turned into a dictionary and returned.
    """
    len_msg = b""
    while True:
        msg_part = client_socket.recv(HEADER_LENGTH)
        if not msg_part:
            break
        len_msg += msg_part
        if len(len_msg) == HEADER_LENGTH:
            break
    
    msg_len = int(len_msg.decode(FORMAT).strip())

    msg = b""
    while True:
        msg_part = client_socket.recv(msg_len)
        if not msg_part:
            break
        msg += msg_part
        if len(msg) == msg_len:
            break
    
    msg = msg.decode(FORMAT)
    msg = json.loads(msg)
    return msg

def send_msg(client_socket: socket.socket, msg):
    """
    Description: This function sends a message to a client socket.
    The message type is json and the message is sent in two parts:
    1. The length of the message
    2. The message itself
    """
    try:
        msg = json.dumps(msg).encode(FORMAT)
        send_msg = f"{len(msg):<{HEADER_LENGTH}}".encode(FORMAT) + msg
        client_socket.sendall(send_msg)
    except Exception as e:
        print(f"[ERROR] sending message: {e}")