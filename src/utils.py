import pickle
import socket

HEADER = 64
FORMAT = 'utf-8'

def receive_msg(conn : socket.socket):
    mesg_length = conn.recv(HEADER)
    if mesg_length:
        mesg_length = int(mesg_length.decode(FORMAT))
        data = conn.recv(mesg_length)
        return pickle.loads(data)

    return None

def send_msg(conn : socket.socket, msg):
    msg = pickle.dumps(msg)
    msg_length = len(msg)
    send_length = str(msg_length).encode(FORMAT)
    send_length += b' ' * (HEADER - len(send_length))
    conn.send(send_length)
    conn.send(msg)