import memory_item as mi
import memory_manager as mm
import server
import socket
import pickle
import multiprocessing as mp
import time
import utils

def test():
    some_address = 'localhost'
    port1 = 5000
    port2 = 5001

    # create servers
    server1 = server.Server(
        (some_address, port1),
        [(0, 100), (100, 200)],
        [(some_address, port1), (some_address, port2)]
    )
    server2 = server.Server(
        (some_address, port2),
        [(0, 100), (100, 200)],
        [(some_address, port1), (some_address, port2)]
    )

    # start servers
    server1_process = mp.Process(target=server1.serve)
    server2_process = mp.Process(target=server2.serve)

    server1_process.start()
    server2_process.start()

    # communicate only through sockets
    time.sleep(1)

#    # test read and write
    # write to server1 through socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((some_address, port1))
        utils.send_msg(s, ("serve_write", 0, 1, True))

        data = utils.receive_msg(s)
        # print result
        print(data)

        utils.send_msg(s, "disconnect")

        data = utils.receive_msg(s)
        # print result
        print(data)
#    # read from server1 through socket
#    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#        s.connect((some_address, port1))
#        s.sendall(pickle.dumps(("serve_read", 0, True)))
#
#        # print result
#        print(pickle.loads(s.recv(1024)))
#
#    # write to server2 through socket
#    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#        s.connect((some_address, port2))
#        s.sendall(pickle.dumps(("serve_write", 100, 2, True)))
#
#        # print result
#        print(pickle.loads(s.recv(1024)))
#
#    # read from server2 through socket
#    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#        s.connect((some_address, port2))
#        s.sendall(pickle.dumps(("serve_read", 100, True)))
#
#        # print result
#        print(pickle.loads(s.recv(1024)))
#
#    # read from server2 by connecting to server1
#    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#        s.connect((some_address, port1))
#        s.sendall(pickle.dumps(("serve_read", 100, True)))
#        # print result
#        print(pickle.loads(s.recv(1024)))
#
#
#    # read from server2 through socket
#    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#        s.connect((some_address, port2))
#        s.sendall(pickle.dumps(("serve_read", 100, True)))
#        # print result
#        print(pickle.loads(s.recv(1024)))

    # test deadlock
    #server1.serve_write(100, 3, True)
    #server2.serve_write(0, 4, True)
    #server1.serve_read(100, True)

    server1_process.join()
    server2_process.join()

if __name__ == "__main__":
    test()
