#!/usr/bin/python3

import sys, socket

from threading import Thread, Lock

class Network:

    SERVER_BASE_PORT = 8000
    CLIENT_BASE_PORT = 9000

    def __init__(uid):
        # get id
        self.uid = uid
        uid_list = uid.split()
        self.node_id = int(uid_list[1])

        # create socket
        self.PRIVATE_TCP_IP = socket.gethostname(socket.gethostname())
        self.is_server = True if uid[0] == 'S' else False
        BASE_PORT = SERVER_BASE_PORT if self.is_server else CLIENT_BASE_PORT
        TCP_PORT = self.node_id + self.BASE_PORT
        self.BUFFER_SIZE = 1024
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(self.PRIVATE_TCP_IP, TCP_PORT)
        self.server.listen(5)
        print(uid, " socket ", self.PRIVATE_TCP_IP, ":", TCP_PORT, " started",
              sep="")

    def send_to_server(dest_id, message):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.PRIVATE_TCP_IP, SERVER_BASE_PORT+dest_id))
            s.send(message)
        except:
            print(self.uid, "connects to Server", dest_id, "failed")

    def send_to_client(dest_id, message):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.PRIVATE_TCP_IP, CLIENT_BASE_PORT+dest_id))
            s.send(message)
        except:
            print(self.uid, "connects to Client", dest_id, "failed")

    def broadcast(message):
        for i in range(num_nodes):
            send_to_server(i, message)

    def receive():
        connection, address = self.server.accept()
        buf = connection.recv(self.BUFFER_SIZE)
        return buf

    def shutdown():
        self.server.close()
        print(self.uid, "socket closed")
